===========
i18nspector
===========

----------------------------------------------
checking tool for gettext POT, PO and MO files
----------------------------------------------

:manual section: 1
:version: i18nspector 0.27.2
:date: |date|

Synopsis
--------
**i18nspector** [*options*] *file* [*file* …]

Description
-----------
**i18nspector** is a tool for checking translation templates (POT), message
catalogues (PO) and compiled message catalogues (MO) files for common problems.
These files are used by the GNU gettext translation functions and tools in
many different development environments.

Options
-------
-l lang, --language lang
   Assume this language. *lang* should be a 2- or 3-letter ISO 639 language
   code, possibly followed by underscore and a 2-letter ISO 3166 territory
   code.
--unpack-deb
   Allow unpacking Debian (binary or source) packages.
-j n, --jobs n
   Use *n* processes in parallel.
   *n* can be a positive integer,
   or ``auto`` to determine the number automatically.
   The default is to use only a single process.
-h, --help
   Show help message and exit.
--version
   Show version information and exit.

Output format
-------------

The following format is used for all the reported problems:

  *code*\ **:** *file*\ **:** *tag* [*extra*]

where:

* *code* is a letter indicating type of the message:
  **E** (error),
  **W** (warning),
  **I** (informative message), or
  **P** (pedantic message);
* *tag* is a name of the problem that was discovered;
* *extra* can contain additional information about the problem.

Tags
----
.. include:: tags.rst

.. |date| date:: %Y-%m-%d

See also
--------
**msgfmt**\ (1), particularly the ``-c`` option

.. vim:ts=3 sts=3 sw=3
