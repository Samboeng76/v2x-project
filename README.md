V2X Message Generation
======================

<mark>\[BAJ: Suggestions:</mark>

1. Add a `toc.md` to make this a CodeChat Editor project.
2. Add links -- V2X, SPaT, MAP, etc. Preferably to protocol, etc.
3. Define data structures. Use CCE to comment each field.
4. How will the messages actually be sent? How should the car respond? Describe
   system test scenarios.
5. Suggested tools: pydantic, uv, ruff, ty\]

Introduction
------------

Vehicle-to-Everything (V2X) communication allows vehicles to exchange
information with other vehicles, roadway infrastructure, and other connected
systems. This information can provide vehicles with information about their
surroundings that may not be available through onboard sensors alone.

There are several types of V2X messages, each intended to communicate different
types of information. These include messages describing vehicle status, traffic
signal states, roadway geometry, and temporary roadway conditions.

This project will focus primarily on **Signal Phase and Timing (SPaT)** and
**Map Data (MAP)** messages. SPaT messages provide information about the current
state and timing of traffic signals, while MAP messages describe the physical
layout of an intersection, including its lanes and movements.

V2X Message Types
-----------------

### Basic Safety Message (BSM)

Basic Safety Messages provide information about a vehicle's current state. This
can include information such as position, speed, heading, and acceleration.
These messages allow other connected vehicles and systems to maintain
information about nearby vehicles.

BSM support may be considered in the future, particularly for vehicle-related
test scenarios and diagnostics.

### Signal Phase and Timing (SPaT)

SPaT messages provide information about traffic signals at an intersection. This
can include the current state of a signal, such as red, yellow, or green, as
well as timing information describing when the signal is expected to change.

A single SPaT message can contain information about multiple movements within an
intersection.

The project will also investigate generating a sequence of SPaT messages as the
state of an intersection changes over time. This would allow the generator to
represent the behavior of a signalized intersection rather than only generating
a single static message.

### Map Data (MAP)

MAP messages describe the physical layout of an intersection. This can include
information about the approaches to an intersection, individual lanes, lane
geometry, and possible movements through the intersection.

MAP messages provide the information needed to understand how the different
lanes and movements within an intersection are arranged.

### Other Message Types

There are also additional V2X message types intended for more specialized
applications. These messages can support functions such as communication between
vehicles and traffic infrastructure.

The initial project will focus on MAP and SPaT messages, while leaving the
possibility of supporting additional message types in the future.

Project Goal
------------

The goal of this project is to develop a **software-based V2X message
generator** capable of creating different types of V2X messages from
user-defined information.

The primary focus will be on generating MAP and SPaT messages for signalized
intersections. The system will provide a way to describe an intersection and its
traffic signals using higher-level information and then generate the
corresponding J2735 <mark>\[BAJ: what is this? Spec link?\]</mark> messages.

Rather than requiring the user to manually construct the underlying ASN.1
message structure, the user will provide information describing the desired
intersection and signal behavior. The generator will then translate this
information into the appropriate J2735 message structure and encode it using
ASN.1 <mark>\[BAJ: spec/link?\]</mark>.

This approach will make it possible to create different intersection
configurations and message contents without manually constructing each
individual encoded message.

Intersection Representation
---------------------------

A central component of the project will be an internal representation of a
signalized intersection.

The representation will provide a higher-level description of the information
needed to generate MAP and SPaT messages. This representation will separate the
way a user describes an intersection from the underlying J2735 and ASN.1
structures.

Information represented by the system may include:

* Intersection location
* Number of approaches
* Number of lanes
* Lane geometry
* Lane width
* Lane attributes
* Allowed movements
* Connections between lanes
* Signalized movements
* Signal groups
* Signal states
* Signal timing
* Intersection identifiers

The exact representation will be developed as part of the project based on the
requirements of the MAP and SPaT message structures.

Configuration
-------------

The message generator will use a user-defined configuration to specify the
information required to generate a V2X message.

The initial configuration format will use structured data such as JSON
<mark>\[BAJ: consider JSON5, which is more human-friendly. Make sure you have a
way to validate the data.\]</mark>. This will allow an intersection to be
described without requiring changes to the underlying message-generation code.

A configuration may contain information describing:

* Intersection geometry
* Lane configuration
* Lane connections
* Signal groups
* Signal states
* Signal timing
* Intersection identifiers
* Other message-specific parameters

For example, a configuration could describe an intersection's approaches, lanes,
movements, and signal behavior. The generator would use this information to
construct the corresponding internal intersection representation.

A future interface, such as a graphical user interface, could be added to make
creating configurations easier, but the message-generation system will not
depend on a GUI.

MAP Message Generation
----------------------

The MAP portion of the project will focus on representing the physical layout of
an intersection.

The system will allow information such as the following to be defined:

* Intersection location
* Number of approaches
* Number of lanes
* Lane geometry
* Lane width
* Lane attributes
* Allowed movements
* Connections between lanes

The message generator will use this information to construct the corresponding
J2735 MAP message.

An important part of the project will be determining how an intersection can be
represented in a way that is both easy to configure and capable of containing
the information needed to describe the intersection accurately.

The resulting MAP message should describe the relationships between approaches,
lanes, and movements in a form that can be interpreted by another V2X system.

SPaT Message Generation
-----------------------

The SPaT portion of the project will focus on representing the state and timing
of traffic signals.

The system will allow information such as the following to be defined:

* Signalized movements
* Current signal state
* Signal timing
* Signal phases

For example, a signal configuration could define the state and timing of several
movements within an intersection.

The generator will use this information to construct the corresponding J2735
SPaT message.

The SPaT system may also support time-based signal behavior, allowing signal
states and timing information to change as the simulation progresses. The
generator could therefore produce a sequence of messages representing the
changing state of an intersection.

This would allow the project to move beyond generating individual static
messages and provide a foundation for testing systems that receive continuously
changing SPaT information.

Relationship Between MAP and SPaT
---------------------------------

MAP and SPaT messages are closely related. MAP messages describe the physical
layout of an intersection, while SPaT messages describe the current state of the
signals controlling movements within that intersection.

The project will investigate how these two types of messages can be generated
consistently for the same intersection.

For example, a lane described by a MAP message may correspond to a particular
movement whose signal state is represented in a SPaT message. Keeping these
relationships consistent will be an important part of the message generation
process.

This relationship will allow MAP and SPaT messages to be generated from a common
representation of an intersection rather than requiring the information to be
defined independently for each message type.

Using a common representation will also make it easier to create complete test
scenarios in which the physical intersection and its signal behavior correspond
to one another.

J2735 and ASN.1 Message Construction
------------------------------------

The generated messages will be based on the appropriate J2735 message
definitions represented using ASN.1.

The message generator will construct the required ASN.1 structures from the
higher-level intersection representation.

For example, generating a SPaT message will involve constructing the appropriate
hierarchy of J2735 structures, beginning with the message frame and continuing
through the SPaT and intersection-specific structures required by the message.

Only the information required by the supported message types will need to be
exposed through the higher-level configuration. The message-generation code will
handle the construction of the underlying ASN.1 structure.

This approach allows the project to use the structure required by the J2735
specification without requiring users to work directly with the complete ASN.1
representation.

Message Generation and Encoding
-------------------------------

The general message generation process will be:

```text
User-defined JSON configuration
              ↓
Intersection representation
              ↓
J2735 message construction
              ↓
ASN.1 encoding
              ↓
Encoded V2X message
```

The project will use the appropriate J2735 ASN.1 definitions and encoding rules
for the supported V2X message types.

The goal is for the generator to produce messages in the encoded form used for
actual V2X communication rather than requiring users to manually construct the
underlying ASN.1 representation.

The encoded message will represent the information provided by the user while
following the structure required by the selected J2735 message type.

Message Output
--------------

The primary output of the message generator will be an **encoded V2X message**
suitable for transmission or use by other V2X systems.

The generated message will be available as raw bytes and/or a hexadecimal
representation.

For example:

```text
02 00 2A 81 03 01 ...
```

The project will also provide functionality for examining and verifying
generated messages. This may include decoding an encoded message and displaying
its contents in a human-readable form for debugging and validation.

The structured representation used internally by the generator is not intended
to replace the encoded message. Its purpose is to allow the software to organize
the user-defined information and construct the appropriate J2735 message before
encoding.

This separation allows users to define an intersection using higher-level
information while the generator handles the construction and encoding of the
actual V2X message.

The resulting architecture will provide a path toward transmitting generated
messages to other systems over an appropriate communication interface.

Validation and Testing
----------------------

Generated messages will need to be verified to ensure that they contain the
information specified by the user and conform to the appropriate message
definitions.

Testing will include verifying:

* Correct construction of MAP messages
* Correct construction of SPaT messages
* Correct relationships between MAP and SPaT information
* Correct signal timing behavior
* Correct ASN.1 encoding
* Correct decoding of generated messages
* Handling of different intersection configurations
* Handling of invalid or incomplete input

Where possible, encoded messages will be decoded and compared against the
original configuration to verify that the information was preserved during
message generation and encoding.

The decoder will also provide a way to inspect generated messages during
development and identify errors in the message construction process.

Automated tests can be added to allow different intersection configurations and
message-generation scenarios to be tested repeatedly.

Expected Outcome
----------------

The final product will be a configurable software-based V2X message generator
capable of producing encoded MAP and SPaT messages from user-defined
intersection and traffic signal information.

The primary objectives are:

1. Develop a representation of a signalized intersection.
2. Define a user-friendly configuration format for describing the intersection.
3. Generate MAP messages from the intersection representation.
4. Generate SPaT messages from signal information.
5. Maintain consistency between MAP and SPaT information.
6. Construct the appropriate J2735 ASN.1 message structures.
7. Encode generated messages using the appropriate ASN.1 encoding rules.
8. Provide a way to examine and verify generated messages.
9. Test generated messages through decoding and comparison with the original
   configuration.
10. Provide a foundation for dynamic message generation, V2X testing, message
    transmission, and simulation.

The resulting system will provide a way to create realistic V2X messages without
manually constructing the underlying J2735 and ASN.1 structures, while also
providing a foundation for future V2X simulation and testing applications.
