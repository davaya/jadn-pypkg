**********************************
JSON Abstract Data Notation (JADN)
**********************************

This package contains software to process JADN Information Models and to validate
and serialize application data.  The software is organized by function:

* **core:** Load, validate, and save a JADN schema.  Constant definitions for the JADN data format.
* **codec:** Validate, encode, and decode application data using a JADN schema.
* **convert:** Convert JADN schema between JSON and documentation formats:

  * text-based Interface Definition Language (IDL)
  * html tables
  * markdown tables

* **transform:** Process a JADN schema to produce another JADN schema:

  * resolve definitions from separate schemas into a single schema (include/import)
  * split a schema that defines multiple objects into separate schemas for each object
  * remove unreferenced definitions
  * remove or truncate comments

* **translate:** Convert a JADN schema into a concrete schema language:

  * JSON Schema
  * XSD*
  * CDDL*
  * Protobuf*

\* Planned

Information Modeling is described in the IoT Semantic Interoperablity 2016 Workshop report,
RFC 8477, https://tools.ietf.org/html/rfc8477.

The JADN IM language is defined in https://github.com/oasis-tcs/openc2-jadn/blob/working/jadn-v1.0-wd01.md.

Quickstart
##########

The quickstart.py script from https://github.com/davaya/jadn-pypkg/tree/master/distribution
illustrates how to use these functions:

* define and validate a schema
* convert the schema into documentation formats
* truncate comments
* translate to JSON Schema
* validate and serialize test messages in:

  * JSON data format
  * Machine-optimized JSON data format