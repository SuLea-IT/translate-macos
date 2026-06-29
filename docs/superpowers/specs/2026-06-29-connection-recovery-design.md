# Connection Recovery and Friendly Runtime Errors Design

## Goal

Make LiveBuddy recover automatically from transient Gemini Live WebSocket interruptions while giving users clear, localized status messages. The app should retry lightweight reconnects without restarting the whole transcript session or rebuilding audio capture unless the user stops manually or the error is terminal.

This follows the product direction: study mature open-source connection handling, borrow algorithms and architecture patterns, then implement LiveBuddy-specific code without copying source or adding dependencies.

## Current State

- `GeminiLiveTranslateClient` reports connection failures through `onStatus` string messages such as `Gemini disconnected`, `Gemini socket closed`, and `Send failed`.
- `AppState.handleClientStatus(_:)` classifies status by substring matching and only updates the UI state.
- If the socket drops after capture starts, audio capture may continue but the Gemini client no longer recovers.
- `stop()` always tears down capture and finishes the transcript session. We should not call `stop()` for a transient reconnect.

## References and Borrowed Ideas

### Socket.IO client reconnection

Repository: https://github.com/socketio/socket.io-client-swift

Relevant ideas to borrow:

- Keep reconnection policy separate from socket event handling.
- Cap retry attempts and delay.
- Do not reconnect after an intentional/manual disconnect.

What we will not copy:

- No Socket.IO protocol, namespace handling, or dependency.

### Alamofire RetryPolicy

Repository: https://github.com/Alamofire/Alamofire

Relevant ideas to borrow:

- Exponential backoff with base delay, multiplier, max retry count, and max delay.
- Treat retry policy as a pure value that can be unit tested.
- Retry only for transient errors, not for authentication/configuration failures.

What we will not copy:

- No HTTP request interceptor or Alamofire dependency.

### Pusher Channels Swift / Starscream style WebSocket lifecycle

Repositories:

- https://github.com/pusher/pusher-websocket-swift
- https://github.com/daltoniam/Starscream

Relevant ideas to borrow:

- Convert low-level socket lifecycle events into typed app-level events.
- Keep raw errors in logs while rendering simpler user-facing messages.
- Let the owner decide whether a close event is recoverable.

What we will not copy:

- No additional WebSocket framework; LiveBuddy continues using `URLSessionWebSocketTask`.

## Design

### Typed connection events

Add `LiveConnectionEvent` in a small model file:

```swift
enum LiveConnectionEvent: Equatable {
    case socketOpened
    case sessionReady
    case disconnected(String)
    case socketClosed(String)
    case sendFailed(String)
    case serverError(String)
    case parseFailed(String)
}
```

Each event exposes:

- `isRecoverable`: true for transient transport errors, false for auth/quota/configuration-like provider errors and parse failures.
- `statusMessage`: short English diagnostic for logs.

Server errors are classified by message text:

- terminal if the message mentions API key, auth, permission, unauthorized, forbidden, quota, billing, invalid argument, or model not found;
- recoverable if the message looks like unavailable, deadline, timeout, internal, 5xx, or overload;
- otherwise terminal to avoid retry storms.

### Retry policy

Add `ConnectionRecoveryPolicy`:

```swift
struct ConnectionRecoveryPolicy: Equatable {
    let maxAttempts: Int
    let initialDelay: TimeInterval
    let multiplier: Double
    let maxDelay: TimeInterval

    func delay(forAttempt attempt: Int) -> TimeInterval
}
```

Default:

- max attempts: 4
- initial delay: 0.75s
- multiplier: 2
- max delay: 8s

No random jitter in this pass. Deterministic delays are easier to test and enough for a single-user desktop app. If many users connect simultaneously this still happens from each local client, not a coordinated fleet.

### Gemini client changes

`GeminiLiveTranslateClient` keeps `onStatus` for existing UI/log behavior and adds:

```swift
var onConnectionEvent: (@Sendable (LiveConnectionEvent) -> Void)?
```

It emits typed events for:

- socket opened;
- session ready;
- socket close;
- receive-loop failure;
- send failure;
- server error message;
- parse failure.

The client still does not own retry logic. It only reports facts.

### AppState reconnect flow

`AppState` owns retry state:

- `connectionRecoveryPolicy`
- `reconnectAttempts`
- `reconnectTask`
- `userInitiatedStop`

Flow:

1. `start()` sets `userInitiatedStop = false`, resets attempts, creates a configured Gemini client.
2. If a recoverable event arrives while `isRunning` and no reconnect is already scheduled:
   - increment attempts;
   - if attempts exceed policy, show localized reconnect-failed status and keep the app in error state;
   - otherwise set status to reconnecting, close the old client, keep capture running, and schedule a new Gemini connect after the delay.
3. On reconnect success:
   - replace `client`;
   - reset attempts;
   - set status to localized connection-recovered;
   - continue using the existing transcript session and existing capture streams.
4. On manual `stop()`:
   - mark `userInitiatedStop = true`;
   - cancel pending reconnect;
   - close client and capture as before;
   - do not schedule reconnect from the close event.
5. On terminal provider error:
   - do not retry;
   - show localized provider error status;
   - keep raw message in logs.

### Localization

Add eight-language UI keys:

- `connectionInterrupted`
- `connectionReconnecting`
- `connectionRecovered`
- `connectionReconnectFailed`
- `connectionProviderError`

### Memory and performance

- No buffering of audio while disconnected. Audio chunks during reconnect are dropped rather than stored to avoid memory growth.
- Only one reconnect task exists at a time.
- Reconnection rebuilds only the Gemini WebSocket client, not screen/mic capture.
- Retry policy is pure and O(1).

## Non-goals

- Offline queueing of audio.
- Full request replay.
- Multiple provider failover.
- Persisted reconnect history.
- Advanced jitter/telemetry dashboard.
