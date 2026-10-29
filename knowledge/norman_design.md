# Norman: Principles of Interaction Design

Workshop summary notes written for teaching. Not a substitute for the original book.

## Affordances in Design
In design, an affordance is a relationship between the properties of an object and the capabilities of a person that determines how the object could be used. A button affords pressing, a slider affords dragging, a text field affords typing. Affordances exist whether or not people notice them, so designers must make the important ones perceivable. In screen interfaces, almost anything can be clicked, which is why visible cues matter more than physical shape.

## Signifiers
A signifier is any perceivable cue that tells people what action is possible and where it should happen: a label, an underline, a raised shadow, an icon, a cursor change. Norman introduced the term to separate the possible action (affordance) from the signal that communicates it. Many usability problems come from missing or misleading signifiers, such as flat text that is actually clickable or a decorative shape that looks like a button. Good interfaces make every interactive element clearly signified and every non-interactive element look inert.

## Mapping
Mapping is the relationship between controls and their effects. Natural mapping uses spatial layout or cultural conventions so the relationship is obvious, for example placing controls in the same arrangement as the things they control, or moving a slider up to increase a value. Poor mapping forces users to memorise or guess. In UI layouts, grouping a control next to the content it changes is a simple way to improve mapping.

## Feedback
Feedback communicates the result of an action: a button changes state, a spinner shows progress, a message confirms a save. Feedback must be immediate, informative, and proportionate; too little leaves users unsure, too much becomes noise. Delayed or missing feedback leads people to repeat actions or assume the system is broken. A sketch of an interface should indicate what the user sees after each important action.

## Constraints
Constraints limit the possible actions so that the right action is easier and errors are harder. Physical constraints (a plug that fits one way), logical constraints (only one remaining option), semantic and cultural constraints all guide behaviour. In software, disabling a button until a form is complete, or offering a dropdown instead of free text, are constraints. Good constraints reduce the need for instructions.

## Conceptual Model
A conceptual model is the user's understanding of how a system works. Designers communicate it through the system image: the visible structure, labels, behaviour and documentation. When the system image clearly expresses a coherent model, users can predict outcomes and recover from errors. Inconsistent layouts or terminology break the conceptual model and make an interface feel unpredictable.

## Discoverability
Discoverability is whether people can figure out what actions are possible and how to perform them. It depends on affordances, signifiers, constraints, mapping, and feedback working together. A screen that relies on hidden gestures or unlabeled icons has low discoverability. When critiquing a UI sketch, ask: could a first-time user find the main action within a few seconds?

## Visual Hierarchy and Gestalt in Interfaces
Gestalt grouping principles shape how users parse a screen. Proximity groups related controls, similarity marks elements with the same function, and alignment creates order. Visual hierarchy uses size, contrast, colour and position to show what matters most, typically one primary action per screen. A clear hierarchy guides the eye in the order the designer intends.
