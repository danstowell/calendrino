#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# load an ical file and render an excerpt from it (centred around today) as a simple HTML page
# (c) Dan Stowell January 2018


# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import os
import calendar
import icalendar
import json
from datetime import date, time, datetime, timedelta, timezone
import pytz
from operator import itemgetter
from html import escape
import hashlib
from time import sleep
from dateutil import rrule
from copy import deepcopy

from extendedhtmlcalendar import ExtendedHTMLCalendar

#############################################
# user settings:

config = json.load(open("config.json"))
verbose = config['verbose']
localtz = pytz.timezone(config.get("timezone", "Europe/Amsterdam"))

with open('template.html', 'r', encoding='utf-8') as myfile:
	htmltemplate = myfile.read().split("{{calendar}}")
assert len(htmltemplate)==2, "HTML template must contain exactly one instance of {{calendar}}"

#############################################

addoneday = timedelta(days = 1) # instantiated here, used later

def _unpack_date_time(dt):
	if isinstance(dt, datetime):
		dt = dt.astimezone(localtz)  # here we convert to the desired timezone for render
		return (dt.date(), dt.time())
	elif isinstance(dt, date):
		return (dt, None)
	else:
		raise ValueError('Unknown date type')

def cmp(a,b):
	return (a > b) - (a < b)

def freqdecoder(val):
	return {
		'YEARLY': rrule.YEARLY,
		'MONTHLY': rrule.MONTHLY,
		'WEEKLY': rrule.WEEKLY,
		'DAILY': rrule.DAILY,
		'HOURLY': rrule.HOURLY,
		'MINUTELY': rrule.MINUTELY,
		'SECONDLY': rrule.SECONDLY,
	}[val]

def get_recurrence_lines(event):
	recurrence_lines = ['RRULE', 'EXRULE', 'RDATE', 'EXDATE']
	for rl in recurrence_lines:
		values = event.get(rl)
		if values:
			if isinstance(values, list):
				for value in values:
					value = value.to_ical().decode('utf-8')
					yield "%s:%s" % (rl, value)
			else:
				value = values.to_ical().decode('utf-8')
				yield "%s:%s" % (rl, value)

def expand_event(event, verbose=False):
	"expands recurring events into each individual instance"
	if 'RRULE' in event:
		event_start = event['DTSTART'].dt
		dtdelta =  event['DTEND'].dt - event_start
		tz = getattr(event_start, 'tzinfo', None)
		if verbose:
			print("    expand_event(): tz is %s --- %s" % (tz, tz.__class__))
		if isinstance(event_start, datetime):
			event_start = event_start.replace(tzinfo=None)

		onerrule = '\n'.join(get_recurrence_lines(event))
		ruleset = rrule.rrulestr(onerrule, dtstart=event_start, forceset=True, ignoretz=True)

		for event_dt_start in ruleset:

			newdate = event_dt_start.date()
			if newdate < startdate:
				continue
			if newdate > enddate:
				return

			newev = deepcopy(event)
			if isinstance(newev['DTSTART'].dt, datetime):
				newev['DTSTART'].dt = localtz.localize(event_dt_start)
				newev['DTEND'  ].dt = localtz.localize((event_dt_start + dtdelta))
			else:
				newev['DTSTART'].dt = event_dt_start.date()
				newev['DTEND'  ].dt = event_dt_start.date() + dtdelta

			if verbose:
				print(getattr(newev['DTSTART'].dt, 'tzinfo'))
			yield newev
	else:
		yield event

def parse_ical_str(icalstr, calsrcclass=''):
	"Adds the desired data to a big 'data' nested-dict which it returns"

	acal = icalendar.Calendar.from_ical(icalstr)

	data = {}
	for component in acal.walk():
		if component.name == "VEVENT":

			verbose = False
			if False: #"CSAI deep" in str(component.get('summary')):
				verbose = True
			if verbose:
				print("verbosely summary:%s" % component.get('summary'))
				print("verbosely dtstart:%s" % component.get('dtstart').dt)

			#for anev in [component]:
			for anev in expand_event(component, verbose): # expands recurring events into each individual instance
				if verbose:
					print("")
					print("  verbosely summary: %s" % anev.get('summary'))
					print("  verbosely dtstart: %s" % anev.get('dtstart').dt)
				dtstart = anev.get('dtstart').dt
				dtend   = anev.get('dtend'  ).dt

				evstart = _unpack_date_time(dtstart)
				evend   = _unpack_date_time(dtend)
				alldayer = evend[1] is None
				if alldayer:
					evend = (evend[0] - addoneday, evend[1]) # because all-day events in ical format have the last day _ex_clusively
				if verbose:
					print("  verbosely time unpacked: %s" % (evstart,)) #.tzid)

				# check both the beginning and end date - only if they're both on the same-side of our range will we skip the event
				stst = cmp(evstart[0], startdate)
				sten = cmp(evstart[0],   enddate)
				enst = cmp(evend[  0], startdate)
				enen = cmp(evend[  0],   enddate)

				nottooearly = enst!=-1
				nottoolate  = sten!=1

				if nottooearly and nottoolate:
					summary = anev.get('summary')
					# foreach day that's touched by this event...
					oneday = evstart[0]
					while oneday <= evend[0]:
						(y, m, d) = oneday.timetuple()[:3]

						# pile up on each day's list of alldays or timeones, along with some kind of flag of whether it extends off the beginning or end. we pile up the description, the location, and timings if relevant
						if y not in data: data[y] = {}
						if m not in data[y]: data[y][m] = {}
						if d not in data[y][m]: data[y][m][d] = ([],[]) # alldayers, timers

						evdata = {
							'summary': summary,
							'location': anev.get('location'),
							'description': anev.get('description'),
							'hasprev': oneday != evstart[0],
							'haspost': oneday != evend[0],
							'calsrcclass': calsrcclass
						}

						if not alldayer:
							evdata['tstart'] = evstart[1]
							evdata['tend'] = evend[1]

						if alldayer:
							data[y][m][d][0].append(evdata)
						else:
							data[y][m][d][1].append(evdata)

						# FINALLY loop increment
						oneday = oneday + addoneday
	del acal
	return data


def mergecaldatas(percaldata):
	data = {}
	for newdata in percaldata:
		# nestedly add this data to the structure
		for y, months in newdata.items():
			if y not in data: data[y] = {}
			for m, days in months.items():
				if m not in data[y]: data[y][m] = {}
				for d, daydata in days.items():
					if d not in data[y][m]: data[y][m][d] = ([],[]) # alldayers, timers
					data[y][m][d][0].extend(daydata[0])
					data[y][m][d][1].extend(daydata[1])
	return data


# then we walk the months we're going to render and call a subclass formatter, writing the results to a html output file. the subclass formatter will output little boxes for each of the items in a day's piles.

def _makeitemtooltip(item):
	toshow = []

	if item['location']:
		toshow.append(item['location'])
	if item['description']:
		toshow.append(item['description'])

	if len(toshow):
		return " title='%s'" % escape("\n\n".join(toshow), quote=True)
	return ''

def render_caldata_html(data):
	with open(config["html_output_file"], "wb") as outfp:
		renderdate = str(datetime.now())
		outfp.write(htmltemplate[0].replace("{{renderdate}}", renderdate).encode("utf-8"))

		for y, months in sorted(data.items()):
			for m, days in sorted(months.items()):

				def callback(day):
					ret = ''
					if (y, m, day) == today.timetuple()[:3]:
						ret += "<a name='today' id='today'></a>"
					if day not in days:
						return ret


					for item in days[day][0]:
						ttl = _makeitemtooltip(item)
						# add markers to differentiate multi-day items
						if item['hasprev'] and item['haspost']:
							longsym = "&#8596;"
						elif item['hasprev']:
							longsym = "&#8677;"
						elif item['haspost']:
							longsym = "&#8676;"
						else:
							longsym = ""

						ret += "<div class='calitem allday %s'%s>%s%s</div>" % (item['calsrcclass'], ttl, longsym, item['summary'])
					ret += "<div class='alldayseparator'></div>"

					for item in sorted(days[day][1], key=itemgetter("tstart")):
						ttl = _makeitemtooltip(item)
						item_tend   = item['tend'].strftime("%H:%M")
						item_tstart = item['tstart'].strftime("%H:%M")
						# add markers to differentiate multi-day items
						if item['hasprev'] and item['haspost']:
							timestr = "..."
						elif item['hasprev']:
							timestr = "...&mdash;%s" % (item_tend)
						elif item['haspost']:
							timestr = "%s&mdash;..." % (item_tstart)
						else:
							timestr = "%s&mdash;%s" % (item_tstart, item_tend)
						ret += "<div class='calitem timed %s'%s><div class='caltime'>%s</div>%s</div>" % (item['calsrcclass'], ttl, timestr, item['summary'])
					return ret

				outfp.write(ExtendedHTMLCalendar().formatmonth(callback, y, m).encode("utf-8"))

		outfp.write(htmltemplate[1].replace("{{renderdate}}", renderdate).encode("utf-8"))



################################################################################################
if __name__=='__main__':
	ical_input_files = {k:os.path.expanduser(fpath) for k,fpath in config['ical_input_files'].items()}

	today = datetime.today().date() - addoneday  # this is simply to force refreshing the data on first invocation


	while True:

		anymodified = False
		daychanged = False

		oldtoday = today

		today = datetime.today().date()

		if today != oldtoday:
			# we definitely want to force a full re-parse since we may need to load data not in prev pass, even if the source files are the same
			anymodified = True
			daychanged = True
			if verbose:
				print("It's a new day, it's a new dawn, it's a new life for me")
			percalmd5 = {k:'' for k in ical_input_files}
			percalmodwhen = {k:0 for k in ical_input_files}
			percaldata = {k:{} for k in ical_input_files}

			# decide the lowest and highest date we'll care about
			startdate = today - timedelta(days = config['view_days_before'])
			enddate   = today + timedelta(days = config['view_days_after'])


		# Loop over the cal source files, deciding whether they need a full re-parse or not
		for calsrcclass, fpath in ical_input_files.items():

			mtime = os.path.getmtime(fpath)
			if not daychanged:
				if mtime == percalmodwhen[calsrcclass]:
					percalmodwhen[calsrcclass] = mtime
					continue  # no need to reload or reparse the data
				if verbose:
					print("mtime mismatch: %s %s" % (mtime, percalmodwhen[calsrcclass]))
			percalmodwhen[calsrcclass] = mtime

			with open(fpath) as infp:
				if verbose:
					print("  loading %s" % calsrcclass)
				icalstr = infp.read()

			onemd5 = hashlib.md5()
			onemd5.update(icalstr.encode('utf-8'))
			onemd5 = onemd5.digest()
			if not daychanged:
				if onemd5 == percalmd5[calsrcclass]:
					percalmd5[calsrcclass] = onemd5
					continue # no need to reparse
				if verbose:
					print("md5 mismatch: %s %s" % (onemd5, percalmd5[calsrcclass]))
			percalmd5[calsrcclass] = onemd5

			anymodified = True
			del percaldata[calsrcclass]
			if verbose:
				print("  parsing %s" % calsrcclass)
			percaldata[calsrcclass] = parse_ical_str(icalstr, calsrcclass) # PARSE
			del icalstr

		if anymodified:
			data = mergecaldatas(percaldata.values())
			if verbose:
				print("  rendering html")
			render_caldata_html(data)
			del data

		sleep(config['sleepdur'])

