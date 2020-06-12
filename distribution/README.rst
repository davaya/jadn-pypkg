**********************************
JSON Abstract Data Notation (JADN)
**********************************

`JADN
<https://github.com/oasis-tcs/openc2-jadn/blob/working/jadn-v1.0-wd01.md>`_
is used to process Information Models as described in
`RFC 8477
<https://tools.ietf.org/html/rfc8477#section-2>`_,
and to validate and serialize Information objects.
The software is organized by function:

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

The quickstart.py script from https://github.com/davaya/jadn-pypkg/tree/master/distribution
illustrates how to use these functions:

* define and validate a schema
* convert the schema into documentation formats
* truncate comments
* translate JADN to JSON Schema
* validate and serialize test messages to:

  * JSON data format
  * Minimized-JSON data format