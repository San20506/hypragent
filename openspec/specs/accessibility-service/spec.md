## Purpose

Provides the Android Accessibility Service with three capabilities: reading the UI node tree for screen state, dispatching gesture commands (tap/swipe/long-press/pinch), and triggering OCR fallback when the node tree is insufficient (empty, sparse, or WebView content). This is Layer A's pure I/O module — it reads and executes, but holds no reasoning logic.

## Requirements

### Requirement: UI Tree Reading

The accessibility service SHALL walk the Android accessibility node tree and serialize it to the MCP `screen_read` tool format. The tree reader is a pure I/O module: it reads screen state but holds no reasoning logic.

#### Scenario: Normal node tree with visible content
- **WHEN** the accessibility service requests the current UI tree for a foreground app with visible interactive elements
- **THEN** it returns a serialized representation containing all visible nodes with their bounds (x, y, width, height), text content, class names, and content descriptions

#### Scenario: Empty node tree
- **WHEN** the accessibility service requests the UI tree and the root node has zero or one children
- **THEN** the tree reader returns an empty result and signals the OCR fallback trigger

#### Scenario: Sparse node tree (e.g., WebView or game surface)
- **WHEN** the accessibility service requests the UI tree and the node count is below a configurable threshold (default: 3 nodes)
- **THEN** the tree reader returns the sparse result and signals the OCR fallback trigger

#### Scenario: Accessibility service not enabled
- **WHEN** the accessibility service is not enabled in Android settings
- **THEN** the tree reader returns an error indicating the service is not active, with no crash or retry loop

### Requirement: Gesture Dispatch

The gesture dispatcher SHALL take a validated command (tap, swipe, long-press, pinch) and issue the corresponding `dispatchGesture` call. It is a pure execution module: it does not decide what to tap, only executes the tap.

#### Scenario: Tap at valid coordinates
- **WHEN** a tap command with valid (x, y) coordinates within screen bounds is received
- **THEN** `dispatchGesture` executes the tap at those coordinates and returns success within 200ms

#### Scenario: Swipe in a direction
- **WHEN** a swipe command with start (x1, y1) and end (x2, y2) coordinates is received
- **THEN** `dispatchGesture` executes a swipe gesture between those points and returns success

#### Scenario: Long-press at coordinates
- **WHEN** a long-press command with valid (x, y) coordinates is received
- **THEN** `dispatchGesture` executes a long-press gesture (hold > 500ms) at those coordinates and returns success

#### Scenario: Pinch gesture
- **WHEN** a pinch command with center coordinates and scale factor is received
- **THEN** `dispatchGesture` executes a pinch gesture and returns success

#### Scenario: Invalid coordinates (out of screen bounds)
- **WHEN** a gesture command with coordinates outside screen bounds is received
- **THEN** the dispatcher returns an error with the invalid coordinates and does not call `dispatchGesture`

#### Scenario: Gesture execution failure
- **WHEN** `dispatchGesture` returns false or throws an exception
- **THEN** the dispatcher returns an error with the failure reason and does not retry automatically

### Requirement: OCR Fallback Trigger

The fallback trigger SHALL decide when the tree read is insufficient and request a raw screenshot for OCR. It is the bridge between the accessibility service and the OCR engine.

#### Scenario: Fallback on empty tree
- **WHEN** the tree reader signals an empty node tree
- **THEN** the fallback trigger requests a full-screen screenshot and queues it for OCR processing

#### Scenario: Fallback on sparse tree
- **WHEN** the tree reader signals a sparse node tree (below threshold) OR the tree has zero interactive nodes (clickable, scrollable, or editable)
- **THEN** the fallback trigger requests a full-screen screenshot and queues it for OCR processing

#### Scenario: Fallback on WebView content
- **WHEN** the tree reader detects the top-level node is a WebView or browser-related class name
- **THEN** the fallback trigger requests a full-screen screenshot and queues it for OCR processing

#### Scenario: No fallback needed
- **WHEN** the tree reader returns a node tree above the threshold with at least one interactive node and the top-level is not a WebView
- **THEN** the fallback trigger does not request a screenshot and the tree result is used directly

#### Scenario: Fallback threshold configurable
- **WHEN** the sparse tree threshold is set to a custom value in configuration
- **THEN** the fallback trigger uses that value instead of the default (3 nodes)

#### Scenario: Intent resolver for consent timing
- **WHEN** Layer A receives a gesture command (tap, swipe) and the consent manager needs to determine the target app
- **THEN** the accessibility service resolves the target app package from the tap coordinates by checking which app's window bounds contain those coordinates, BEFORE the gesture is executed
