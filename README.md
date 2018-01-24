
Calendrino
==========

A script to monitor some iCal files (.ics) and to render a simple easy-to-read calendar of events.

Copyright (c) Dan Stowell 2018


Requirements
------------

* Python 3
* also the "icalendar" python package

Tested with Python 3.5.2 running on Linux.


How to use
----------

1. Edit "config.json" to specify the paths that you want the ical files to come from.
2. Run the main script e.g. by opening a terminal window and running "python3 calendrino_render.py".
3. Once the files have been processed at least once, open the output file "rendered.html" using a web browser.

The script will always do a fresh render once you invoke it. Thereafter it keeps running, and if any of the input files changes it will detect it and re-render the output file.

The script is designed to be low on CPU and memory demands, so it should hopefully be OK to leave it running in the background. For example, it does not re-render if the input file contents haven't actually changed.


Specification
-------------

Calendrino is designed for this purpose:

* All my calendar software is rubbish in that it renders way too slowly. When I flick from one month to the next it takes a second, or ten seconds, to render (this may be because my ical files have thousands of events in, but I make no apology for that!). The few seconds it takes to render a calendar breaks concentration. So, what we want is something that watches a specified set of iCal files, rendering out a fixed easily-viewable file (such as HTML or PDF) that can be viewed in pereptually instantaneous time. The file should include not everything, but a reasonable window of time that I normally need to look at, e.g. a few months/weeks in the future and in the past.
* It should be trivially easy to jump to "today" in the render and to be able to identify it visually. Right now this works via a simple visual highlight on the day, but also by the fact that a shift-refresh on the HTML page if we're navigated to "#today" always jumps back to it.
* It should not waste much memory or cpu. I minimise cpu by monitoring for changed ical files, rather than aggressively re-rendering them too often.
* It should be easy to search. I do this by piggybacking on web browser or pdf reader ctrl+f.


Licence
-------

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

