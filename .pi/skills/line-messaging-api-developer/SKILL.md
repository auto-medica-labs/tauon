---
description: Helps developers integrate, implement, and debug the LINE Messaging API in Python with the line-bot-sdk. Use for API clients, authentication, webhook events, replies, pushes, rich menus, Flex messages, profiles, content, group chats, signature validation, framework integration, tests, and deployment.
metadata:
    github-path: line-messaging-api-developer
    github-ref: refs/heads/main
    github-repo: https://github.com/dheerapat/skills
    github-tree-sha: d67516262536a681581ed8c6917ee827fa29606d
name: line-messaging-api-developer
---
# LINE Messaging API Developer

Act as an API integration guide for LINE bot developers. Design the smallest correct API integration first, then add product behavior. Prefer the SDK's current `linebot.v3` API and the official Messaging API reference.

## First inspect

Before editing:

1. Identify whether the task is webhook ingestion, outbound messaging, content/profile access, rich-menu management, Flex payloads, or another Messaging API endpoint.
2. Identify the app framework and whether its handlers are synchronous or asynchronous.
3. Find the dependency file, environment configuration, API client lifecycle, and tests.
4. Reuse the existing application structure; do not replace the framework or add a new abstraction without need.
5. Check that `line-bot-sdk` is installed and that the project uses Python 3.10+.

Ask for the missing endpoint, framework, or authentication mode only when it cannot be inferred from the repository.

## SDK rules

Use current v3 imports:

```python
from linebot.v3 import WebhookParser, WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    ApiClient, Configuration, MessagingApi,
    ReplyMessageRequest, TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent
```

For async frameworks use `AsyncApiClient` and `AsyncMessagingApi`, and await API calls. Do not introduce deprecated `LineBotApi`, `linebot.api`, or legacy event/message models in new code. Do not edit generated files under `linebot/v3/*/models` or `linebot/v3/*/api`; SDK generation owns those files.

Credentials must come from environment or the host's secret manager:

```text
LINE_CHANNEL_SECRET
LINE_CHANNEL_ACCESS_TOKEN
```

Never commit credentials, print tokens, or disable signature verification in production.

## API surface

Choose the SDK client and operation that match the API contract instead of issuing ad-hoc HTTP:

- `MessagingApi`: reply, push, multicast, narrowcast, broadcast, profile lookup, group/room operations, webhook endpoint settings, quotas, and rich-menu metadata.
- `MessagingApiBlob`: download user-sent image/video/audio content and upload rich-menu images.
- `AsyncApiClient` and async API classes: use in async frameworks; await every request.
- `Configuration(access_token=...)`: supplies the channel access token and optional host/transport settings.

Use the official reference for required fields, limits, permissions, status codes, and endpoint-specific constraints. Preserve request IDs and useful status information when diagnosing API failures.

## Webhook contract

The callback must:

- read the exact raw request body before JSON parsing;
- read `X-Line-Signature` and reject invalid signatures with HTTP 400;
- parse with `WebhookParser(channel_secret)`;
- handle every event safely, including unknown and non-message events;
- return a successful response after processing.

Minimal synchronous pattern:

```python
parser = WebhookParser(channel_secret)
configuration = Configuration(access_token=channel_access_token)

@app.post("/callback")
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    try:
        events = parser.parse(body, signature)
    except InvalidSignatureError:
        abort(400)

    with ApiClient(configuration) as api_client:
        line_api = MessagingApi(api_client)
        for event in events:
            if isinstance(event, MessageEvent) and isinstance(event.message, TextMessageContent):
                reply = bot_reply(event.message.text)
                line_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text=reply)],
                    )
                )
    return "OK"
```

For FastAPI or aiohttp, read and decode the raw body, use an `AsyncMessagingApi`, and `await line_api.reply_message(...)`. Keep the API client lifecycle appropriate to the framework; a long-lived async client should be closed during application shutdown.

## API integration behavior

Keep product/domain logic separate from transport code:

- A small service handles intent/state; the webhook or API adapter translates events and requests.
- Use `event.source.user_id`, `group_id`, or `room_id` as identifiers when state or profile APIs are needed.
- Treat `reply_token` as single-use and short-lived. Reply to the event when possible; use `push_message` only when there is no reply token or the message is later/initiated by the bot.
- Send no more than five message objects in one request. Select reply, push, multicast, narrowcast, or broadcast based on the recipient semantics; do not use multicast for group chats.
- Use `MessagingApiBlob` for binary message content and rich-menu image operations; use `MessagingApi` for JSON APIs.
- Handle follow, postback, join, unsend, and non-text events explicitly or safely ignore them. Do not assume every event has `message.text` or `reply_token`.
- Validate and bound user-controlled input before passing it to external services or constructing messages.

Use typed v3 models for messages (`TextMessage`, `ImageMessage`, templates, Flex messages, etc.) rather than hand-building JSON. Follow the generated method and model signatures in the installed SDK and official LINE API documentation. For response status, headers, and `x-line-request-id`, use the generated `*_with_http_info` method.

## Rich menus

Treat rich-menu setup as an explicit provisioning task, not something the webhook recreates on every request. The normal flow is:

1. Prepare a compliant image and map its pixel coordinates to tappable areas.
2. Create a `RichMenuRequest` with `RichMenuSize`, `RichMenuBounds`, and actions such as `URIAction`, `MessageAction`, or `RichMenuSwitchAction`.
3. Upload the image through `MessagingApiBlob.set_rich_menu_image(...)` with the correct content type.
4. Set it globally with `MessagingApi.set_default_rich_menu(...)`, or link it to a user with `link_rich_menu_id_to_user(...)`.

Example model imports:

```python
from linebot.v3.messaging import (
    MessagingApiBlob, RichMenuRequest, RichMenuArea, RichMenuSize,
    RichMenuBounds, URIAction,
)
```

Store the returned rich-menu ID, make provisioning idempotent, and do not upload the image or create duplicate menus during normal message handling. Rich-menu buttons can open HTTPS URLs, send postback data, or switch aliases; route resulting postback events through the same signature-validated webhook.

## Flex messages

Use Flex Messages for custom layouts and interactive cards. Build a `FlexBubble` or `FlexCarousel` from typed components, wrap it in `FlexMessage(alt_text=..., contents=...)`, and send it like any other message:

```python
from linebot.v3.messaging import (
    FlexMessage, FlexBubble, FlexBox, FlexText, FlexButton, URIAction,
)

bubble = FlexBubble(
    body=FlexBox(
        layout="vertical",
        contents=[FlexText(text="Hello", weight="bold", size="xl")],
    ),
    footer=FlexBox(
        layout="vertical",
        contents=[FlexButton(action=URIAction(label="Open", uri="https://example.com"))],
    ),
)
message = FlexMessage(alt_text="Hello", contents=bubble)
```

Prefer the LINE Flex Message Simulator for design, then deserialize validated simulator JSON with `FlexContainer.from_json(...)` when that is simpler than constructing a large component tree. Keep `alt_text` useful for accessibility and clients that cannot render Flex. Use HTTPS for all media and action URLs, validate user-controlled values before inserting them into Flex content, and test the serialized payload.

## Testing checklist

Add or update tests for:

1. valid signature and invalid signature;
2. text event routing and reply text;
3. non-text/unknown events not crashing the callback;
4. outbound API calls mocked or directed at a local test server;
5. missing credentials and malformed payloads.

Do not make real LINE API calls in tests. Preserve the raw request body when testing signature validation.

## Delivery checklist

Before finishing:

- verify the callback URL is public HTTPS and matches the configured LINE webhook URL;
- confirm webhook delivery is enabled and the channel token has the required permissions;
- document required environment variables and local run commands;
- run the project's formatter, linter, and tests;
- report any checks blocked by missing dependencies or external LINE configuration.

If changing the SDK itself rather than a bot application, update the source-of-truth files and tests. Generated v3 changes require the repository's OpenAPI generation workflow; never patch generated output as a permanent fix.
