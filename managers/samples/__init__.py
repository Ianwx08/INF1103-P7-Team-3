"""Example found items for demos and manual testing, loaded without any Gemini call.

Sample data is demo/test data, not a user report: it skips Gemini on purpose (to save API
tokens), but every sample is turned into the same JSON shape Gemini returns and checked by
the same SchemaValidator before it is stored. Reports typed into the app still always go
through Gemini.
"""
