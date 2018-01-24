
from calendar import HTMLCalendar

class ExtendedHTMLCalendar(HTMLCalendar):
	"Just like HTMLCalendar except the rendering sub-functions pass around a callback which will be used to render additional info in each day"

	def formatday(self, callback, day, weekday):
		"""
		Return a day as a table cell.
		"""
		if day == 0:
			return '<td class="noday">&nbsp;</td>' # day outside month
		else:
			return '<td class="%s">%d%s</td>' % (self.cssclasses[weekday], day, callback(day))

	def formatweek(self, callback, theweek):
		"""
		Return a complete week as a table row.
		"""
		s = ''.join(self.formatday(callback, d, wd) for (d, wd) in theweek)
		return '<tr>%s</tr>' % s

	def formatmonth(self, callback, theyear, themonth, withyear=True):
		"""
		Return a formatted month as a table.
		"""
		v = []
		a = v.append
		a('<table border="1" cellpadding="0" cellspacing="0" class="month">')
		a('\n')
		a(self.formatmonthname(theyear, themonth, withyear=withyear))
		a('\n')
		a(self.formatweekheader())
		a('\n')
		for week in self.monthdays2calendar(theyear, themonth):
			a(self.formatweek(callback, week))
			a('\n')
		a('</table>')
		a('\n')
		return ''.join(v)

	def formatyear(self, theyear, width=3):
		raise NotImplementedError() # since we'd want to add the extensions there too

