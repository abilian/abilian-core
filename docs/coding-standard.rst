Coding standard
===============

We recommend using the PEP8 and Google coding standard, with the following exceptions:

- Indentation should be 2 chars, not 4.

Additional rules
----------------

TODO


Notes
-----

Line length
^^^^^^^^^^^

We stick to the "no lines longer than 80 characters" rule despite the fact that
we're living in a post VT-220 world.

Here's `some rationale <http://www.reddit.com/r/programming/comments/2nkntp/does_column_width_80_make_sense_in_2014/cmf3f9s>`_ by user "badsector" on Reddit:

  I used to use a 120 character limit or ignore E501 on my pep8 checker (python), but eventually went back to the default 80 character limit. I realized it did more for me than let me fit 4 files side by side on a laptop screen:

  - It discouraged me from writing long sprawling if statements and method chains.
  - With less space, I thought more assigning about clear and concise names for things.
  - I would break out deeply nested ifs and other control statements into separate functions. This is probably the biggest win since smaller code pieces are easier to unit test due to lowered cyclomatic complexity.