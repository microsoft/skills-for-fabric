# Plan Definition HTTP JSON Handling

Apply this guidance to public Get Definition responses and their LRO status and
result responses. It does not retrieve narrative values or authorize token
exchange, private APIs, additional requests or changes to the Plan.

## Decode the delivered body

Choose stages from the body currently delivered by the HTTP client, not only
from the original headers. Reassess this boundary on follow-up questions.

| Delivered body | Remaining stages |
|---|---|
| Raw gzip-compressed bytes | gzip, then strict UTF-8, then strict JSON |
| Already decompressed JSON bytes | strict UTF-8, then strict JSON; no gzip stage |
| Parsed JSON object | Validate the actual status and operation-specific response |

`Content-Type: application/json` declares the representation, not successful
parsing. `Content-Encoding: gzip` describes wire compression and can remain in
headers after the client decompresses the body. `curl --compressed` delivers
decompressed output; do not decompress it again based on that retained header.
For raw bytes, check the captured encoding or gzip magic prefix `1f 8b`.
A UTF-8 error at byte `0x8b` alone does not establish gzip.

Reject unsupported encodings, corrupt or truncated gzip, invalid UTF-8,
duplicate JSON keys, nonfinite numbers and malformed JSON. Do not replace
invalid characters, discard fields or treat decoding failure as an empty result.
The offline `plan_definition.py` helper validates a JSON definition envelope;
it is not an HTTP client or a raw-gzip decoder. When the task supplies the
decoding command or forbids shell commands, do not open or run the helper or
any other script to inspect it.

After HTTP decoding, separately decode each `InlineBase64` definition part as
strict UTF-8 JSON. HTTP gzip and part Base64 are different encoding layers.
Follow the definition workflow's complete-envelope, identity and LRO checks.

## Handle response failures without replay

- An unsupported curl option rejected before transmission is a local command
  construction failure, not a service rejection or authentication failure.
  Do not use `--location-trusted=false` as a portable way to disable redirects.
  Do not enable credential forwarding with `--location-trusted`.
- A parsing exception after receipt is a response-decoding failure. Decode the
  already received body rather than replaying the Get Definition POST, renewing
  credentials or switching endpoints solely to repair local parsing.
- If the body is unavailable, report the gap rather than automatically issuing
  another request. Keep credentials and complete response bodies out of logs.
- Successful JSON parsing is not operation completion. Validate the actual
  status and complete response; a 202 acknowledgement still requires the
  authorized LRO workflow. Saved definitions and response metadata never
  establish current measured values, source freshness or live-query proof.

During definition retrieval, preserve the distinction between original wire encoding and remaining decoding
stages. Follow the requested output contract on every turn: raw JSON means no
Markdown code fences, progress prose or trailing explanation.
