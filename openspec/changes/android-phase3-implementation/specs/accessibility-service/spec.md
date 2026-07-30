## ADDED Requirements

### Requirement: UI Tree Reading

The accessibility service SHALL walk the Android accessibility node tree and serialize it to the MCP `screen_read` tool format.

#### Scenario: Normal node tree with visible content
- **WHEN** the accessibility service requests the current UI tree for a foreground app with visible interactive elements
- **THEN** it returns a serialized representation containing all visible nodes with their bounds, text content, class names, and content descriptions

#### Scenario: Empty node tree
- **WHEN** the accessibility service requests the UI tree and the root node has zero or one children
- **THEN** the tree reader returns an empty result and signals the OCR fallback trigger

#### Scenario: Sparse node tree
- **WHEN** the tree count is below a configurable threshold (default: 3) OR the tree has zero interactive nodes
- **THEN** the fallback trigger requests a full-screen screenshot for OCR

#### Scenario: Accessibility service not enabled
- **WHEN** the accessibility service is not enabled in Android settings
- **THEN** the tree reader returns an error with no crash or retry loop

### Requirement: Gesture Dispatch

The gesture dispatcher SHALL take a validated command and issue the corresponding `dispatchGesture` call.

#### Scenario: Tap at valid coordinates
- **WHEN** a tap command with valid coordinates within screen bounds is received
- **THEN** `dispatchGesture` executes the tap and returns success within 200ms

#### Scenario: Swipe in a direction
- **WHEN** a swipe command with start and end coordinates is received
- **THEN** `dispatchGesture` executes the swipe and returns success

#### Scenario: Long-press at coordinates
- **WHEN** a long-press command with valid coordinates is received
- **THEN** `dispatchGesture` executes a long-press (hold > 500ms) and returns success

#### Scenario: Pinch gesture
- **WHEN** a pinch command with center coordinates and scale factor is received
- **THEN** `dispatchGesture` executes a pinch and returns success

#### Scenario: Invalid coordinates
- **WHEN** a gesture command with coordinates outside screen bounds is received
- **THEN** the dispatcher returns an error and does not call `dispatchGesture`

#### Scenario: Gesture execution failure
- **WHEN** `dispatchGesture` returns false or throws an exception
- **THEN** the dispatcher returns an error and does not retry automatically

### Requirement: OCR Fallback Trigger

The fallback trigger SHALL decide when the tree read is insufficient and request a raw screenshot for OCR.

#### Scenario: Fallback on empty tree
- **WHEN** the tree reader signals an empty node tree
- **THEN** the fallback trigger requests a full-screen screenshot for OCR

#### Scenario: Fallback on sparse tree
- **WHEN** the tree reader signals a sparse node tree (below threshold) OR zero interactive nodes
- **THEN** the fallback trigger requests a full-screen screenshot for OCR

#### Scenario: Fallback on WebView content
- **WHEN** the tree reader detects the top-level node is a WebView
- **THEN** the fallback trigger requests a full-screen screenshot for OCR

#### Scenario: No fallback needed
- **WHEN** the tree reader returns a rich node tree above threshold with interactive nodes
- **THEN** the fallback trigger does not request a screenshot

#### Scenario: Fallback threshold configurable
- **WHEN** the sparse tree threshold is set to a custom value
- **THEN** the fallback trigger uses that value instead of the default

#### Scenario: Intent resolver for consent timing
- **WHEN** Layer A receives a gesture command and the consent manager needs to determine the target app
- **THEN** the accessibility service resolves the target app package from the tap coordinates by checking which app's window bounds contain those coordinates, BEFORE the gesture is executed
