mhist
=====

What
----
Solution to record and query history of whatever has been played with mpv, with support for aggregating records from multiple systems.

Why
---
Keeping track of what has been already watched, and when is not easy, it's even more troublesome when one uses multiple devices to do so. There was a need that can seamlessly support checking what has been played on any of the synchronized systems.

How
---
mhist is a Python script that hooks into mpv via a small lua script that simply makes mpv send each loaded file name / URL into 'mhist record'. The mhist then creates file structure using hostname as part of the structure, and write the records to files there, making it possible to record multiple entries on many hosts at the same time, and then synchronize those directories to aggregate all the records. The synchronization part is to be handled with another tool, for example, Syncthing.

Quick start
-----------

::

  ./mhist deploy --enable

::

  ./mhist query --with-words 'SomeSeries s2'

::

  ./mhist query --fuzzy yukiyuuuuuuna

Options and switches
--------------------
::

  % mhist -h
  usage: mhist [-h] {record,query,deploy} ...
  
  optional arguments:
    -h, --help            show this help message and exit
  
  Actions:
    {record,query,deploy}
      record              Record entry.
      query               Query the saved history.
      deploy              Control integration with mpv
  
  % mhist record -h
  usage: mhist record [-h] (--from-string FROM_STRING | --from-stdin)
  
  optional arguments:
    -h, --help            show this help message and exit
  
  Required either of:
    --from-string FROM_STRING
                          Take record from string passed as argument.
    --from-stdin          Read items to record from stdin, separated by new
                          line.
  
  % mhist query -h
  usage: mhist query [-h] [--limit LIMIT] [--fuzzy-ratio FUZZY_RATIO]
                     (--fuzzy FUZZY | --with-words WITH_WORDS | --last)
  
  optional arguments:
    -h, --help            show this help message and exit
    --limit LIMIT         Print at most N matching/latest records. Set to 0 to
                          print all. Default is 10.
    --fuzzy-ratio FUZZY_RATIO
                          When --fuzzy is in use, accept entries that reach >= N
                          partial ratio. Default is 63.
  
  Required either of:
    --fuzzy FUZZY         Case insensitive fuzzy search, processes list from
                          newest to oldest entry.
    --with-words WITH_WORDS
                          Split passed string by spaces, check if all of the
                          words are present in entry, in any order and case
                          insensitive.
    --last                List last entries
  
  % mhist deploy -h
  usage: mhist deploy [-h] (--enable | --disable)
  
  optional arguments:
    -h, --help  show this help message and exit
  
  Required either of:
    --enable    Create ~/.mpv/scripts/mhist.lua with global mhist or local path
                to mhist script.
    --disable   Remove ~/.mpv/scripts/mhist.lua.


