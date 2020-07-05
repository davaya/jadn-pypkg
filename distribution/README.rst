**********************************
JSON Abstract Data Notation (JADN)
**********************************

`JADN
<https://github.com/oasis-tcs/openc2-jadn/blob/working/jadn-v1.0-wd01.md>`_ is an
`information modeling
<https://tools.ietf.org/html/rfc8477#section-2>`_ language used to define the information
needed by applications and to serialize that information using one or more data formats.
It has several purposes, including convenient and expressive definition of data structures,
validation of data instances, providing hints for user interfaces working with structured data,
and facilitating protocol internationalization. A JADN specification consists of two parts:
an Information Model (abstract schema) that is independent of data format,
and serialization rules that define how to represent information using a specific data format.
A single JADN schema defines protocol data in multiple formats including XML and JSON,
plus a CBOR format that is actually *concise*. Serialization rules can be developed
for additional data formats, allowing any JADN specification to use them.

The software in this package is organized by function:

* **core:** Load, validate, and save a JADN schema.
* **codec:** Validate, encode, and decode application information using a specified data format:

  * Idiomatic (verbose) JSON
  * Minimized (concise) JSON
  * CBOR*
  * XML*

* **convert:** Convert JADN schema between JSON and documentation formats:

  * text-based Interface Definition Language (IDL)
  * html tables
  * markdown tables

* **transform:** Process a JADN schema to produce another JADN schema:

  * combine definitions from separate schemas into a single schema
  * split a schema that defines multiple objects into separate schemas for each object
  * remove unused definitions
  * delete or truncate comments

* **translate:** Convert a JADN schema into a concrete schema language:

  * JSON Schema
  * XSD*
  * CDDL*
  * Protobuf*

\* Planned

Quickstart
##########

The `quickstart.py
<quickstart.py>`_
script illustrates how to use these functions:

* define and validate a schema
* convert the schema to and from documentation formats
* truncate comments
* translate a JADN schema to JSON Schema
* validate messages and serialize using multiple data formats:

  * JSON
  * Minimized JSON

Feedback
########

Comments on this software can be submitted using `GitHub
<https://github.com/davaya/jadn-pypkg>`_ issues and pull requests.

The JADN specification is being developed by the OASIS OpenC2 Technical Committee. OASIS members may
participate directly in its development; others may participate indirectly using GitHub issues or the
`openc2-comment
<https://www.oasis-open.org/committees/tc_home.php?wg_abbrev=openc2>`_ public mailing list.