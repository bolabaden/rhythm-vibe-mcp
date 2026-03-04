# Vendor Libraries — Expert Reference

This document provides deep technical analysis of every vendored library in this repository. It is intended as an expert-level reference for developers integrating, extending, or reasoning about the audio algorithms, data models, and pipelines represented here.

Each library section is self-contained and covers: purpose, architecture, key algorithms/data structures, parameter spaces, integration surface, and notes on relevance to `rhythm-vibe-mcp`.

---

## Table of Contents

1. [dawproject](#dawproject) — Bitwig's open DAW project exchange format (XML/ZIP)
2. [JUCE](#juce) — *(to be documented)* Cross-platform C++ audio application framework
3. [link](#link) — *(to be documented)* Ableton Link: wireless, tempo-synchronized multi-device beat clock
4. [lmms](#lmms) — *(to be documented)* Linux MultiMedia Studio: open-source DAW and its plugin/pattern engine
5. [rubberband](#rubberband) — *(to be documented)* High-quality audio time-stretch and pitch-shift library
6. [stargate](#stargate) — *(to be documented)* Stargate DAW (formerly MusiKernel): sequencer + synthesis engine
7. [tenacity](#tenacity) — *(to be documented)* Tenacity: community fork of Audacity with extended audio editing capabilities
8. [tracktion_engine](#tracktion_engine) — *(to be documented)* JUCE-based C++ audio engine powering the Tracktion/Waveform DAW

---

## dawproject

> **Repository origin:** `vendor/dawproject/`  
> **Upstream:** [github.com/bitwig/dawproject](https://github.com/bitwig/dawproject)  
> **Version:** 1.0 (stable)  
> **License:** MIT  
> **Language:** Java 21 (JAXB-annotated DOM; schema-generated)  
> **Build:** Gradle 8.x (`./gradlew build`)  
> **Format status:** Ratified, in production use across 6 major DAWs

### Overview

DAWproject is a **vendor-agnostic, lossless project exchange format** for Digital Audio Workstations. It is designed to transfer the full creative state of a music production session — audio clips, MIDI notes, note expressions, automation, plug-in states, mixer topology, and clip-launcher content — across different DAW applications with maximum fidelity.

It occupies a unique niche that no prior format fills:

| Capability              | DAWproject | Standard MIDI | AAF (Advanced Authoring Format) |
|-------------------------|:----------:|:-------------:|:-------------------------------:|
| Intended domain         | Music Production | MIDI Sequencing | Video Post |
| Time model              | Beats + Seconds (mixed) | Beats only | Seconds only |
| Audio clips + fades     | ✓          | —             | ✓ |
| Time warping of audio   | ✓          | —             | — |
| Pitch transpose         | ✓          | —             | — |
| Note data               | ✓          | ✓             | — |
| Per-note expressions    | ✓          | —             | — |
| Full plug-in state      | ✓          | —             | — |
| Generic built-in devices| ✓          | —             | — |
| Clip launcher / scenes  | ✓          | —             | — |
| Automation ramps        | ✓ (linear + hold) | Only CC/SysEx | Volume/Pan |

### File Format Architecture

```
song.dawproject        (ZIP archive)
├── project.xml        (primary project data, UTF-8 XML)
├── metadata.xml       (song metadata: title, artist, album, …)
├── audio/             (embedded audio files — path chosen by exporter)
│   └── Drumloop.wav
└── plugins/           (plug-in preset blobs)
    └── <uuid>.vstpreset
```

- **Container:** ZIP (standard `java.util.zip`)  
- **Serialization:** JAXB 4.x (`jakarta.xml.bind`), human-readable indented XML  
- **Encoding:** UTF-8 with BOM strip on load  
- **Schemas:** `Project.xsd` and `MetaData.xsd` (generated from the JAXB-annotated Java DOM via `DawProject.exportSchema()`)  
- **Extension:** `.dawproject`

Audio and video media files may be embedded inside the ZIP or referenced externally (`FileReference.external = true`) with either absolute or relative paths. Plug-in state is **always embedded**.

---

### Object Model — Full Class Hierarchy

The Java package `com.bitwig.dawproject` (and sub-packages `device`, `timeline`) defines the entire document object model. All classes are JAXB-annotated and drive both XML serialization and XSD schema generation.

#### Root Document

```
Project                          (root element; version="1.0")
  Application                    (name + version of exporting DAW)
  Transport
    Tempo        : RealParameter  (unit=bpm, min, max, value)
    TimeSignature: TimeSignatureParameter  (numerator, denominator)
  Structure      : List<Lane>    (Track | Channel at top level)
  Arrangement                    (linear timeline)
  Scenes         : List<Scene>   (clip-launcher scenes)
```

#### Inheritance Tree

```
Nameable  (name, color, comment)
└── Referenceable  (id : xs:ID)
    ├── Parameter  (abstract; parameterID)
    │   ├── RealParameter    (value, min, max, unit: Unit)
    │   ├── BoolParameter    (value: boolean)
    │   ├── IntegerParameter (value, min, max: int)
    │   ├── EnumParameter    (value, count, labels[])
    │   └── TimeSignatureParameter (numerator, denominator)
    ├── Lane  (abstract)
    │   ├── Track   (contentType[], channel, nested Track[])
    │   └── Channel (role, audioChannels, volume, pan, mute, solo, destination, sends[], devices[])
    └── Timeline  (abstract; timeUnit, track reference)
        ├── Lanes   (polymorphic container: List<Timeline>)
        ├── Clips   (List<Clip>)
        ├── Notes   (List<Note>)
        ├── Points  (automation: target + List<Point>)
        ├── Warps   (content + List<Warp> — see Time-Warp Engine)
        ├── Audio   (File + channels, sampleRate, duration, algorithm)
        ├── Video   (File + channels, sampleRate, duration, algorithm)
        ├── ClipSlot (hasStop, optional Clip — clip launcher)
        └── Markers  (List<Marker>)
```

---

### The Time-Warp Engine

The most algorithmically significant construct in DAWproject is the **`Warps`/`Warp`** system, which provides a general-purpose **piecewise-linear time mapping** between two temporal coordinate systems.

#### Formal Definition

A `Warps` element defines a bijective, piecewise-linear mapping:

```
f : T_outer → T_inner
```

where:
- `T_outer` uses `timeUnit` (beats or seconds) — the "outside" timeline
- `T_inner` uses `contentTimeUnit` (beats or seconds) — the "inside" content

The mapping is specified by an ordered list of `Warp` anchor points `(time_i, contentTime_i)`. Between anchors, **linear interpolation** is applied. The content timeline is fully encapsulated inside the `Warps` and addressed only through this mapping.

#### Canonical Use Case: Audio Stretch-to-Grid

```xml
<Clip time="0" duration="8">
  <Warps contentTimeUnit="seconds" timeUnit="beats">
    <Audio channels="2" duration="2.823" sampleRate="48000">
      <File path="audio/Drumloop.wav"/>
    </Audio>
    <Warp time="0.0" contentTime="0.0"/>
    <Warp time="8.0" contentTime="2.823"/>
  </Warps>
</Clip>
```

This maps beat [0, 8] → seconds [0.0, 2.823], effectively stretching a 2.823-second audio file to fill 8 beats (a tempo-sync operation, delegated to the importing DAW's stretch algorithm). The `algorithm` attribute on `Audio` hints which stretch algorithm was used by the exporter (e.g., `"stretch"`).

#### Multi-Point Non-Linear Warping

With more than two anchor points, the mapping becomes multi-segment piecewise linear, enabling:
- **Manual warp markers** (Ableton-style beat-to-time pinning)
- **Rubberband-free tempo mapping** of live recorded audio
- **Per-beat groove quantization** without destroying original timing

```
beats:   0    2    4     6    8
         ↕    ↕    ↕     ↕    ↕
seconds: 0   0.9  1.6   2.1  2.823
```

Each segment between adjacent warp points is independently stretched, enabling non-uniform time compression/expansion while keeping anchor points rhythmically aligned.

#### Beat-in-Beat Warping (Nested Clips)

`Warps` may also map `beats → beats`, enabling **nested loop and offset** structures where inner content has its own beat grid distinct from the outer arrangement timeline.

#### Important Implementation Notes

- Minimum of **2 warp points** required for a valid mapping
- `Warp.time` is in `Warps.timeUnit` coordinates
- `Warp.contentTime` is in `Warps.contentTimeUnit` coordinates
- The **content element** (Audio, Notes, etc.) is a direct child of `Warps`, not a sibling
- The DAW importing the project is responsible for performing the actual time-stretch; DAWproject merely records the mapping

---

### Clip Architecture

`Clip` is the fundamental unit of timeline content. It is a `Nameable` (not a `Referenceable`) but supports ID-based shared content via `reference`.

```
Clip
  time           : double       (position on parent timeline, in parent's timeUnit)
  duration       : double       (length on parent timeline)
  contentTimeUnit: TimeUnit      (beats | seconds — of clip's own content)
  playStart      : double       (trim start in content coordinates)
  playStop       : double       (trim stop in content coordinates)
  loopStart      : double       (loop region start)
  loopEnd        : double       (loop region end)
  fadeTimeUnit   : TimeUnit      (unit for fade times)
  fadeInTime     : double
  fadeOutTime    : double
  enable         : boolean
  reference      : IDREF→Timeline  (alias clip — shared content with another clip's content)
  content        : Timeline     (one of: Notes, Clips, Audio, Video, Warps, Points, Markers, Lanes)
```

**Alias Clips:** When `reference` is set, the clip reuses the referenced timeline's content without duplication. The clip's own `time`, `duration`, and loop/fade attributes still apply as region selectors on that shared content.

**Nested Clips:** A `Clip` containing `Clips` as its content creates two-level hierarchy (outer clip = region on arrangement; inner clips = events within the region). Bitwig Studio uses this for audio tracks where each clip in the arrangement contains a sub-timeline of audio events.

---

### Note & Note Expression System

`Note` extends the classic MIDI note model with **per-note expression timelines**:

```
Note
  time     : double   (position in parent Notes timeline)
  duration : double
  channel  : int      (MIDI channel 0-based)
  key      : int      (MIDI pitch 0–127)
  vel      : double   (Note On velocity, normalized 0.0–1.0)
  rel      : double   (Note Off / release velocity, normalized 0.0–1.0)
  content  : Timeline (optional; per-note expression data)
```

Per-note content is typically a `Points` timeline targeting one of the **expression types** (see Automation below), enabling MPE-like per-note modulation that is superior to standard CC-based MIDI:

- `gain` — per-note amplitude envelope
- `pan` — per-note stereo position
- `transpose` — per-note pitch offset in semitones
- `timbre` — per-note timbre (e.g., CC74 / MIDI 2.0 brightness)
- `formant` — per-note formant shift
- `pressure` — per-note channel pressure / aftertouch
- `polyPressure` — per-note polyphonic pressure (key-specific)
- `pitchBend` — per-note pitch bend (full resolution)

This model is a strict superset of both MIDI 1.0 and MPE, and maps cleanly to MIDI 2.0 per-note expressions.

---

### Automation System

Automation is expressed as `Points` timelines. A `Points` element contains:

1. **`AutomationTarget`** — declares what is being automated:
   - `parameter` (IDREF to any `RealParameter`, `BoolParameter`, etc.) — direct parameter reference
   - `expression` (ExpressionType enum) — MIDI-style expression
   - `channel` (int) — MIDI channel
   - `key` (int) — for `polyPressure`
   - `controller` (int 0-based) — for `channelController` (CC number)

2. **`List<Point>`** — typed automation points, all of the same concrete type:
   - `RealPoint(time, value, interpolation)` — float automation; `interpolation` = `linear` or `hold`
   - `BoolPoint(time, value)` — boolean toggle (e.g., mute)
   - `IntegerPoint(time, value)` — integer step automation
   - `EnumPoint(time, value)` — enumeration index
   - `TimeSignaturePoint(time, numerator, denominator)` — meter changes

3. **`unit : Unit`** — the unit of `RealPoint.value` (decibel, normalized, hertz, etc.)

#### Interpolation

| Mode     | Behavior |
|----------|----------|
| `linear` | Ramp between current and next point value |
| `hold`   | Step: hold current value until next point |

This eliminates the staircase artifacts of MIDI CC automation when converted from a DAW's native ramp curves.

#### Automation Scoping

A `Points` timeline can live at three levels:
- **Arrangement level** — global tempo/time-signature automation via `Arrangement.tempoAutomation` / `timeSignatureAutomation`
- **Track lane level** — per-track parameter or MIDI expression automation
- **Inside a Clip** — automation data scoped to a clip's content (enables per-clip modulation)

---

### Device & Plugin System

The `Channel.devices` list is a **polymorphic device chain** supporting heterogeneous device types in a single chain:

```
Device  (abstract base)
  deviceName    : String  (human-readable)
  deviceVendor  : String
  deviceID      : String  (format-specific ID, e.g., plug-in ID)
  deviceRole    : DeviceRole
  loaded        : boolean
  Parameters    : List<Parameter>  (automatable parameter declarations)
  Enabled       : BoolParameter
  State         : FileReference    (opaque preset blob path in ZIP)

  ├── Plugin  (abstract; adds pluginVersion)
  │   ├── Vst2Plugin   (VST2 — identified by deviceID=uniqueID integer)
  │   ├── Vst3Plugin   (VST3 — identified by deviceID=FUID string)
  │   ├── ClapPlugin   (CLAP — identified by deviceID=plugin.id string)
  │   └── AuPlugin     (Audio Unit — identified by deviceID=type/subtype/manufacturer)
  │
  └── BuiltinDevice  (abstract; portable generic devices)
      ├── Equalizer   (n-band parametric EQ)
      ├── Compressor  (dynamics compressor)
      ├── NoiseGate   (downward expander/gate)
      └── Limiter     (peak/brick-wall limiter)
```

**Device roles** classify the device's signal flow position:

| Role         | Signal Path |
|--------------|-------------|
| `instrument` | MIDI → Audio generator |
| `noteFX`     | MIDI → MIDI transformer (arpeggator, chord, etc.) |
| `audioFX`    | Audio → Audio processor |
| `analyzer`   | Audio → no output (metering, spectrum) |

**Plugin state** is stored as an opaque binary blob (the DAW's native preset format) embedded in the ZIP at `State.path`. The blob format is plug-in-format-specific:
- VST2: raw bank/program chunk bytes
- VST3: `IBStream` state bytes  
- CLAP: `clap_plugin_state` extension bytes
- AU: Audio Unit preset data

This ensures **100% parameter fidelity** even for complex synthesizers: if both exporting and importing DAW have the plug-in installed, the full patch state is preserved exactly.

---

### Built-in Generic Devices (Portable Signal Processing)

For interoperability when a specific plug-in is not available on the target DAW, DAWproject defines **four generic device abstractions** that any DAW can render with its own native DSP equivalents:

#### Equalizer

Multi-band parametric EQ. Each `EqBand` has:

| Parameter | Type | Unit | Notes |
|-----------|------|------|-------|
| `Freq`    | RealParameter | Hz | Center / corner frequency |
| `Gain`    | RealParameter | dB | Band gain (shelves, bell) |
| `Q`       | RealParameter | linear | Bandwidth / resonance |
| `Enabled` | BoolParameter | — | Per-band bypass |
| `type`    | EqBandType | — | See below |
| `order`   | int | — | Filter order (slope) |

**EQ Band Filter Types:**

| Type | Description |
|------|-------------|
| `highPass`  | High-pass filter (attenuates below Freq) |
| `lowPass`   | Low-pass filter (attenuates above Freq) |
| `bandPass`  | Band-pass filter (passes around Freq) |
| `highShelf` | High-shelf filter (boosts/cuts above Freq) |
| `lowShelf`  | Low-shelf filter (boosts/cuts below Freq) |
| `bell`      | Peaking / parametric bell (boost/cut around Freq) |
| `notch`     | Notch filter (attenuates at Freq) |

Additionally: `InputGain` and `OutputGain` (both `RealParameter`, unit=dB) for pre/post gain staging.

#### Compressor

Standard feed-forward dynamics compressor:

| Parameter     | Unit   | Notes |
|---------------|--------|-------|
| `Threshold`   | dB     | Level above which compression begins |
| `Ratio`       | percent (0–100) | Compression ratio (e.g., 4:1 = 25%) |
| `Attack`      | seconds | Onset of gain reduction |
| `Release`     | seconds | Recovery after gain reduction |
| `InputGain`   | dB     | Pre-compression gain/drive |
| `OutputGain`  | dB     | Post-compression makeup gain |
| `AutoMakeup`  | bool   | Automatic makeup gain enable |

#### NoiseGate (Downward Expander)

| Parameter   | Unit   | Notes |
|-------------|--------|-------|
| `Threshold` | dB     | Level below which gating begins |
| `Ratio`     | percent (0–100) | Expansion ratio |
| `Attack`    | seconds | Onset of attenuation |
| `Release`   | seconds | Recovery |
| `Range`     | dB (−∞ to 0) | Maximum gain reduction depth |

#### Limiter

| Parameter     | Unit   | Notes |
|---------------|--------|-------|
| `Threshold`   | dB     | Peak ceiling |
| `Attack`      | seconds | Onset of limiting |
| `Release`     | seconds | Recovery |
| `InputGain`   | dB     | Pre-limiter gain |
| `OutputGain`  | dB     | Post-limiter output trim |

---

### Mixer Architecture

The mixer is described by the **`Structure`** section of the project (a list of top-level `Track` / `Channel` objects) combined with `Channel.destination` routing references.

#### Channel

```
Channel (extends Lane)
  role          : MixerRole    (regular | master | effect | submix | vca)
  audioChannels : int          (1=mono, 2=stereo, …)
  volume        : RealParameter  (unit=linear, typical range 0–2 representing 0–+6 dB)
  pan           : RealParameter  (unit=normalized, 0.5=center)
  mute          : BoolParameter
  solo          : boolean
  destination   : IDREF→Channel  (output bus routing)
  sends         : List<Send>
  devices       : List<Device>  (insert chain)
```

#### Mixer Roles

| Role      | Description |
|-----------|-------------|
| `regular` | Standard audio/instrument track channel |
| `master`  | Master bus / main output |
| `effect`  | Return/aux effect bus |
| `submix`  | Sub-mix / group bus |
| `vca`     | VCA (Voltage Controlled Amplifier) fader — controls gain of linked channels without audio signal passing through it |

#### Send

```
Send (extends Referenceable)
  destination : IDREF→Channel
  type        : SendType  (pre | post)
  Volume      : RealParameter
  Pan         : RealParameter (optional)
  Enable      : BoolParameter (optional)
```

`pre` = pre-fader send (independent of fader); `post` = post-fader send (affected by fader position).

---

### Parameter & Unit System

All automatable values are wrapped in typed `Parameter` subclasses that encode semantic units alongside the value.

**Unit enumeration:**

| Value        | Meaning |
|--------------|---------|
| `linear`     | Raw linear scale (e.g., gain multiplier 0.0–2.0) |
| `normalized` | 0.0–1.0 range (common for panning, filter amount) |
| `percent`    | 0–100 range (ratio, depth) |
| `decibel`    | dBFS or dB gain |
| `hertz`      | Frequency in Hz |
| `semitones`  | Pitch offset in semitones |
| `seconds`    | Time duration |
| `beats`      | Musical time in quarter-note beats |
| `bpm`        | Tempo in beats per minute |

**Double special values:** The `DoubleAdapter` class serializes `Double.POSITIVE_INFINITY` as `"inf"` and `Double.NEGATIVE_INFINITY` as `"-inf"` to support parameters like noise gate range `(-inf dB)` without special casing.

---

### Track Content Types

`Track.contentType` is a **set** (`xs:list`) of `ContentType` values, declaring what kinds of timelines the track can host:

| Type         | Description |
|--------------|-------------|
| `audio`      | Audio clips / waveforms |
| `notes`      | MIDI-style note data |
| `automation` | Automation lanes |
| `video`      | Video clips |
| `markers`    | Cue/locator markers |
| `tracks`     | Nested sub-tracks (folder track) |

A track may declare multiple content types (e.g., `"audio notes"` for a track that can hold both).

---

### Arrangement vs. Clip Launcher

DAWproject represents both the **linear arrangement** (horizontal timeline) and the **clip launcher** (session/matrix view) in the same document:

```
Project
  Arrangement                (linear timeline — the "song")
    Lanes (timeUnit=beats)
      Lanes (track=id_X)
        Clips                (clip timeline for track X)
          Clip               (region at beat position)
    Markers                  (cue markers / locators)
    TempoAutomation          (Points with tempo ramp data)
    TimeSignatureAutomation  (Points with meter changes)

  Scenes []                  (clip launcher scenes/rows)
    Scene
      content : Timeline     (a Clips or Lanes or ClipSlot structure)
```

Each `Scene` represents a horizontal row in the session view. `ClipSlot` elements within a `Clips` timeline represent individual cells; `ClipSlot.hasStop` models a stop button slot.

---

### Java API Reference

The `DawProject` utility class is the primary entry point:

```java
// Save a project (ZIP):
DawProject.save(project, metadata, embeddedFiles, outputFile);

// Save project.xml only (debugging):
DawProject.saveXML(project, xmlFile);

// Load from .dawproject ZIP:
Project project = DawProject.loadProject(file);
MetaData meta   = DawProject.loadMetadata(file);

// Load an embedded binary blob (e.g., plug-in state):
byte[] blob = DawProject.loadEmbedded(file, "plugins/abc123.vstpreset");

// Validate project against generated XSD:
DawProject.validate(project);

// Export XSD schema (regeneration):
DawProject.exportSchema(new File("Project.xsd"), Project.class);
```

**Building (Java 21 required):**

```bash
cd vendor/dawproject
./gradlew build       # compiles, tests, generates docs
./gradlew test        # runs DawProjectTest, GenerateDocumentationTest, LoadDawProjectTest
```

**Dependencies:**
- `jakarta.xml.bind:jakarta.xml.bind-api:4.0.2` — JAXB API
- `com.sun.xml.bind:jaxb-impl:4.0.5` — JAXB reference implementation
- `commons-io:commons-io:2.18.0` — BOM-stripping on load
- `therapi-runtime-javadoc` — runtime Javadoc introspection (for schema docs generation)
- `j2html` + `reflections` (test only) — HTML reference doc generation

---

### Metadata Schema (`metadata.xml`)

The companion `MetaData` document stores song-level identification:

```xml
<MetaData>
  <Title>My Song</Title>
  <Artist>Artist Name</Artist>
  <Album>Album Name</Album>
  <OriginalArtist>Original Artist</OriginalArtist>
  <Composer>Composer</Composer>
  <Songwriter>Songwriter</Songwriter>
  <Producer>Producer</Producer>
  <Arranger>Arranger</Arranger>
  <Year>2025</Year>
  <Genre>Electronic</Genre>
  <Copyright>© 2025</Copyright>
  <Website>https://example.com</Website>
  <Comment>Notes</Comment>
</MetaData>
```

All fields are optional strings.

---

### DAW Compatibility (as of v1.0)

| DAW | Version | Notes |
|-----|---------|-------|
| Bitwig Studio | 5.0.9+ | Reference implementation / exporter |
| PreSonus Studio One | 6.5+ | Full support |
| Steinberg Cubase | 14+ | Full support |
| Steinberg Cubasis | 3.7.1+ | Mobile (iOS/Android) |
| Steinberg VST Live | 2.2+ | Live performance |
| n-Track Studio | 10.2.2+ | Mobile + desktop |

**Third-party converters:**
- [DawVert](https://github.com/SatyrDiamond/DawVert) — converts between DAWproject and many other DAW formats
- [ProjectConverter](https://github.com/git-moss/ProjectConverter) — Cockos Reaper ↔ DAWproject

---

### Design Principles & Non-Goals

**Goals:**
- Preserve the **maximum amount of user-created data** possible
- Export the track/timeline **structure as-is** from the source DAW (flattening is the importer's responsibility)
- **Language agnostic** (XML/ZIP, no special binary dependencies)
- **Open and free** (MIT licensed)

**Non-goals:**
- Native DAW file format (not optimized for real-time read/write)
- Binary performance (deliberately text XML for readability/debuggability)
- Low-level MIDI events (uses higher-level `Note` and `ExpressionType` abstractions)
- View state, preferences, or UI settings

---

### Integration Notes for `rhythm-vibe-mcp`

DAWproject is directly relevant to `rhythm-vibe-mcp` as an **import/export pipeline** for full project state:

1. **Round-trip project interchange** — generate a `Project` object from `rhythm-vibe-mcp`'s internal models and serialize it to `.dawproject` for consumption by Bitwig, Studio One, or Cubase.

2. **Time-warp data for stretch planning** — the `Warps` / `Warp` model precisely represents beat-to-seconds mappings generated from tempo analysis, warping algorithms, or user-defined groove quantization. This maps directly to the output of pitch/time stretch planning stages.

3. **Note expression authoring** — `rhythm-vibe-mcp`'s theory engine can produce per-note `Points` timelines with `transpose`, `timbre`, `pressure`, and `pitchBend` expression curves, enabling MPE-quality output from music theory generation.

4. **Automation pipeline** — the `Points` + `AutomationTarget` model can represent generated automation curves (dynamics, filter sweeps, pan motion) in a way that survives round-tripping across DAWs.

5. **Built-in device normalisation** — when generating processing chains, `Equalizer`, `Compressor`, `NoiseGate`, and `Limiter` objects provide a DAW-neutral parameter vocabulary for describing spectral shaping and dynamics, regardless of which specific plug-in the target DAW uses.

6. **File format integration** — `DawProject.loadProject()` can be used within `rhythm-vibe-mcp`'s parsers to ingest `.dawproject` files from users, extracting note content, automation, and audio references for further music-theory analysis.

---

## JUCE

> **Repository origin:** `vendor/JUCE/`  
> **Status:** Uninitialized git submodule — directory contains only `.git` metadata.  
> **Upstream:** [github.com/juce-framework/JUCE](https://github.com/juce-framework/JUCE)  
> *(Documentation will be populated once the submodule is initialized with `git submodule update --init vendor/JUCE`)*

---

## link

> **Repository origin:** `vendor/link/`  
> **Upstream:** [github.com/Ableton/link](https://github.com/Ableton/link)  
> **Version:** Mainline (2025)  
> **License:** GPLv2+ / Proprietary dual-license  
> **Language:** C++17, header-only (plus optional C extension `abl_link`)  
> **Build:** CMake; `include/` + `modules/asio-standalone/` added to include path  
> **Platforms:** macOS/iOS, Windows, Linux, ESP32, any POSIX/STL platform

### Overview

Ableton Link is a **wireless, decentralized beat-clock synchronization protocol** that maintains a shared tempo and quantized beat grid across multiple applications running on one or more devices connected over a local network. It is production-grade technology embedded in Ableton Live, and its source is available as an SDK for third-party integration.

Key properties:
- **Peer-to-peer** — no server or master clock; every peer participates equally
- **Auto-discovery** — peers find each other automatically via UDP multicast
- **Continuous** — the timeline advances at all times, even when transport is stopped; start/stop state is a separate optional layer
- **Quantized launch** — tempo and phase changes snap to the next quantum boundary when other peers are present
- **Latency-compensated** — each peer adds its own output latency when computing beat/time mappings, so audio events hit the speaker at the same wall-clock moment
- **Realtime-safe** — the per-callback API path (`captureAudioSessionState` / `commitAudioSessionState`) never blocks

---

### Architecture Overview

```
┌────────────────────────────────────────────────────────────────────┐
│                        Application Layer                           │
│  captureAudioSessionState() ←──→ commitAudioSessionState()         │
│  SessionState: beatAtTime(), phaseAtTime(), timeAtBeat()           │
└──────────────────────────┬─────────────────────────────────────────┘
                           │ (lock-free triple-buffer)
┌──────────────────────────▼─────────────────────────────────────────┐
│                      Controller / ApiController                    │
│  • Maintains local Timeline (tempo, beatOrigin, timeOrigin)        │
│  • Converts between host time ↔ ghost time via GhostXForm          │
│  • Manages SessionController, Sessions, Peers, Gateways            │
└──────────────────────────┬─────────────────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────────────────┐
│                      Network / Discovery Layer                     │
│  • UDP multicast (discovery::Service) for peer announcement        │
│  • UDP unicast (PingResponder / Measurement) for RTT estimation    │
│  • Payload serialization: big-endian binary packets                │
└────────────────────────────────────────────────────────────────────┘
```

---

### Core Data Model

#### `Timeline` — The Beat/Time Bijection

`Timeline` is the central algebraic object. It establishes a **linear bijection between wall-clock microseconds and beat values**:

```cpp
struct Timeline {
  Tempo  tempo;       // beats per minute
  Beats  beatOrigin;  // beat value at the anchor
  microseconds timeOrigin;  // host time at the anchor

  Beats toBeats(microseconds time) const {
    return beatOrigin + tempo.microsToBeats(time - timeOrigin);
  }
  microseconds fromBeats(Beats beats) const {
    return timeOrigin + tempo.beatsToMicros(beats - beatOrigin);
  }
};
```

The `(tempo, beatOrigin, timeOrigin)` triple fully characterizes a constant-tempo mapping. It is serialized over the network using big-endian binary encoding (the `NetworkByteStreamSerializable` concept).

**Wire format:** Tempo is transmitted as `microseconds-per-beat` (a `std::chrono::microseconds` integer), not as BPM, to avoid floating-point rounding ambiguity. Valid tempo range: **20–999 BPM** (enforced by `clampTempo()`)

#### `Beats` — Fixed-Point Beat Arithmetic

```cpp
struct Beats {
  // Internal: int64_t micro-beats (1 beat = 1,000,000 micro-beats)
  explicit Beats(double beats)  : mValue(llround(beats * 1e6)) {}
  double floating() const { return mValue / 1e6; }
  std::int64_t microBeats() const { return mValue; }
  // All arithmetic ops work on mValue (integer, no float drift)
};
```

Fixed-point representation prevents floating-point drift over long sessions. Beat values are unique per-instance (the absolute magnitude is private); only **phase** (beat modulo quantum) is shared.

#### `Tempo`

```cpp
struct Tempo {
  double bpm() const;
  microseconds microsPerBeat() const; // = 60e6 / bpm
  Beats microsToBeats(microseconds) const;
  microseconds beatsToMicros(Beats) const;
};
```

Tempo converts between beats and microseconds. The wire representation is `microsPerBeat()` (integer), not `bpm()` (float).

---

### Clock Synchronization Algorithm

#### Phase 1 — Ghost Time (Shared Virtual Clock)

The core clock-sync problem: each device has its own system clock that **drifts** relative to all others. Link solves this by establishing a **"ghost time"** — a virtual global clock defined by a linear affine transform from local host time:

```cpp
struct GhostXForm {
  double slope;          // relative clock rate (≈1.0 for well-behaved clocks)
  microseconds intercept; // offset in ghost-time domain

  microseconds hostToGhost(microseconds hostTime) const {
    return microseconds{llround(slope * hostTime.count())} + intercept;
  }
  microseconds ghostToHost(microseconds ghostTime) const {
    return microseconds{llround((ghostTime - intercept).count() / slope)};
  }
};
```

The ghost clock is **not tied to any single device's hardware** — it is an emergent shared reference computed independently by each peer from the same measured data.

#### Phase 2 — Round-Trip Time Measurement (Ping/Pong)

To estimate the `GhostXForm` for a peer, Link uses an **iterative ping-pong protocol** (`Measurement.hpp`):

1. Local peer sends a **Ping** containing its local host time `T_h1`
2. Remote peer replies with a **Pong** containing:
   - The ghost time it assigned to receiving the ping: `T_g`
   - Its own local host time when it replied: `T_h_remote`
   - The previously forwarded ghost time: `T_g_prev`
3. Local peer records `T_h2 = now()` and computes:

```
offset_sample = T_g - (T_h1 + T_h2) / 2
```

This is **NTP-style midpoint estimation**: the ghost time is assumed to be at the midpoint of the round trip in local host time.

Parameters: **100 data points** collected across **5 measurement rounds** (50 ms timer between rounds). The final `GhostXForm` is derived from the median of the collected offsets, making it **outlier-robust**.

#### Phase 3 — Per-Sample Jitter Filtering (HostTimeFilter)

The audio callback is not invoked at perfectly regular intervals — jitter is introduced by OS scheduling. `HostTimeFilter` eliminates this jitter by maintaining a **rolling least-squares linear regression** over the last 512 `(sampleTime, hostTime)` pairs:

```cpp
template <typename Clock, typename NumberType, std::size_t kNumPoints = 512>
class BasicHostTimeFilter {
  // Circular buffer of 512 (sampleTime, hostTimeMicros) pairs
  // Each call to sampleTimeToHostTime() adds a point and recomputes
  // the regression, returning hostTime = slope*sampleTime + intercept
};
```

The `linearRegression()` function computes ordinary least squares in O(N) using running sums:

```
slope     = (N·ΣXY - ΣX·ΣY) / (N·ΣX² - (ΣX)²)
intercept = (ΣY - slope·ΣX) / N
```

This produces a smoothed, jitter-free estimate of the current host time given a sample index, suitable for use in the audio callback.

---

### Session Management

#### Session Identity and Selection

Each peer belongs to exactly one **session**, identified by a `SessionId` (UUID). When two sessions merge, the winning session is selected by:

1. **Ghost time age**: the session with the **larger ghost-time value** (i.e., the older/longer-running session) wins — preserving the established beat grid
2. **Fallback**: if ghost times are within 500 ms of each other, **numerically smaller SessionId** wins (deterministic UUID comparison)

The 500 ms epsilon (`SESSION_EPS`) prevents fringe cases where clock measurement imprecision could flip the session decision.

#### Remeasurement

Active sessions are **remeasured every 30 seconds** to track long-term clock drift (clocks drift at different rates due to temperature, load, etc.)

#### Client vs. Session Timeline

Two timeline representations coexist:

| | Description |
|--|--|
| **Session Timeline** | Shared across the network; expressed in ghost time; used as the source of truth for phase alignment |
| **Client Timeline** | Local to the application; expressed in host time; computed from the session timeline via `GhostXForm` |

The function `updateClientTimelineFromSession()` performs the conversion:

```cpp
// Compute new client timeline that:
// (a) continues from the current beat value at atTime (no beat jump)
// (b) adopts the session tempo
// (c) encodes beat-zero of the session timeline in its (timeOrigin, beatOrigin)
//     so that phase quantization is globally coherent
```

The **beat-zero anchor** is critical: it ensures that `beatAtTime(t) % quantum` yields the same phase on all peers, even though each peer has a different absolute `beatAtTime(t)` value.

---

### Phase, Quantization & Quantized Launch

#### Phase Functions (`Phase.hpp`)

```cpp
// phase(b, q) = b mod q, but correct for negative beats
Beats phase(Beats beats, Beats quantum);

// nextPhaseMatch: smallest x' > x with phase(x', q) == phase(target, q)
Beats nextPhaseMatch(Beats x, Beats target, Beats quantum);

// closestPhaseMatch: nearest x' to x with matching phase (may be < x)
Beats closestPhaseMatch(Beats x, Beats target, Beats quantum);

// toPhaseEncodedBeats: align a timeline beat to the nearest quantum grid point
Beats toPhaseEncodedBeats(const Timeline& tl, microseconds time, Beats quantum);
```

The **quantum** parameter is the period of the repeating grid (e.g., `4.0` for a 4-beat loop). **Phase (= beat mod quantum)** is the same value on all peers at any given wall-clock moment.

#### `requestBeatAtTime` — Quantized Launch

```cpp
void requestBeatAtTime(double beat, microseconds time, double quantum);
```

Behavior:
- **No peers:** immediately maps `beat` to `time` (the current moment)
- **With peers:** maps `beat` to the **next time where the session phase matches**  `fmod(beat, quantum)` — i.e., waits for the next quantum boundary before making a transition visible

This is the mechanism that enables **quantized clip launch**: triggering a loop that begins exactly on the next downbeat, in sync with all connected devices.

#### `forceBeatAtTime` — Unconditional Remap

Force-maps a beat to a specific time, broadcasting immediately to all peers. Anti-social (disrupts other peers) — intended only for **bridging external clock sources** (e.g., MTC, MIDI clock) into a Link session.

---

### Latency Compensation Model

Proper latency compensation requires understanding three different timestamps:

| Timestamp | Meaning | Correction |
|-----------|---------|------------|
| Audio callback invocation time | When the OS invoked the callback | Add output latency |
| Buffer submission time (macOS/iOS `mHostTime`) | When audio buffer goes to hardware | Add output latency |
| Speaker output time | When audio hits ears | **This is the sync target** |

The correct value to pass to Link methods is:
```
beatAtTime(hostTime + outputLatency, quantum)
```

`SampleTiming` utility converts between sample index and host-time microseconds for an audio buffer:

```cpp
struct SampleTiming {
  double sampleAtTime(microseconds time) const;
  microseconds timeAtSample(double sample) const;
  microseconds mBufferBegin;
  double mSampleRate;
};
```

Combined with `HostTimeFilter`, this enables accurate per-sample beat position calculation with < 3 ms alignment error (as required by the test plan).

---

### LinkAudio Extension (2025)

`LinkAudio` extends the base `Link` class with **real-time audio streaming** synchronized to the Link beat grid:

```
LinkAudio
  enableLinkAudio(bool)       — enable audio transport
  setPeerName(string)         — identify peer in session UI
  channels()                  — list of discovered audio channels
  setChannelsChangedCallback  — notified on channel appear/disappear

LinkAudioSink  (sender side)
  write(BufferHandle)         — write interleaved int16 PCM samples
  anchor(beat, quantum)       — attach buffer to a beat-grid position

LinkAudioSource  (receiver side)
  read(BufferHandle)          — read interleaved int16 PCM samples
  resizeBuffer(numSamples)    — set receive buffer size
```

**Audio format:** Interleaved 16-bit signed integer PCM (`int16_t`)  
**Encoder:** `link_audio::PCMCodec` — lossless direct int16 encoding (no compression)  
**Transport:** UDP, using the same ASIO context as the beat-sync protocol  
**Alignment:** `BeatTimeMapping` maps received buffers onto the session beat grid so audio from different peers is sample-accurate once latency is accounted for

Sinks only transmit when at least one source is subscribed. Audio buffers carry beat-time anchors from the sender so receivers can align them to the same grid position.

---

### C Language Extension (`abl_link`)

For integration into non-C++ hosts (embedded firmware, game engines, scripting language FFI), an `extern "C"` wrapper is provided in `extensions/abl_link/include/abl_link.h`:

```c
// Opaque handle types
typedef struct abl_link   { void *impl; } abl_link;
typedef struct abl_link_session_state { void *impl; } abl_link_session_state;

// Lifecycle
abl_link abl_link_create(double bpm);
void     abl_link_destroy(abl_link link);

// Session control
void     abl_link_enable(abl_link link, bool enable);
void     abl_link_enable_start_stop_sync(abl_link link, bool enabled);
uint64_t abl_link_num_peers(abl_link link);
int64_t  abl_link_clock_micros(abl_link link);  // microseconds

// Callbacks (invoked on Link-managed thread)
void     abl_link_set_tempo_callback(abl_link, abl_link_tempo_callback, void *ctx);
void     abl_link_set_num_peers_callback(abl_link, abl_link_num_peers_callback, void *ctx);
void     abl_link_set_start_stop_callback(abl_link, abl_link_start_stop_callback, void *ctx);

// Session state capture/commit (audio thread)
void     abl_link_capture_audio_session_state(abl_link, abl_link_session_state);
void     abl_link_commit_audio_session_state(abl_link, abl_link_session_state);

// Beat/time/phase queries
double   abl_link_tempo(abl_link_session_state);
void     abl_link_set_tempo(abl_link_session_state, double bpm, int64_t at_time);
double   abl_link_beat_at_time(abl_link_session_state, int64_t time, double quantum);
double   abl_link_phase_at_time(abl_link_session_state, int64_t time, double quantum);
int64_t  abl_link_time_at_beat(abl_link_session_state, double beat, double quantum);
void     abl_link_request_beat_at_time(abl_link_session_state, double beat,
                                        int64_t time, double quantum);
void     abl_link_force_beat_at_time(abl_link_session_state, double beat,
                                      int64_t time, double quantum);
```

This enables Python (via ctypes/cffi), Rust (via c2rust/bindgen), Lua, or any language with C FFI to participate in a Link session.

---

### Platform Clock Implementations

| Platform | Header | Clock Source |
|----------|--------|--------------|
| macOS/iOS | `platforms/darwin/Clock.hpp` | `mach_absolute_time()` (Mach kernel monotonic) |
| Windows | `platforms/windows/Clock.hpp` | `QueryPerformanceCounter()` |
| Linux | `platforms/linux/Clock.hpp` | `CLOCK_MONOTONIC` via `clock_gettime()` |
| ESP32 | `platforms/esp32/Clock.hpp` | `esp_timer_get_time()` |
| Generic STL | `platforms/stl/Clock.hpp` | `std::chrono::steady_clock` |

All clocks expose `.micros()` returning `std::chrono::microseconds`. The Darwin and Windows clocks specifically provide sub-microsecond resolution that is then smoothed by the `HostTimeFilter`.

For Windows, the ASIO audio driver (`Steinberg ASIO SDK 2.3`) is strongly recommended because it provides explicit buffer submission timestamps, eliminating the need to query `QueryPerformanceCounter()` at callback invocation time.

---

### Build Requirements

| Platform | Minimum Compiler | Optional |
|----------|-----------------|----------|
| Windows | MSVC 17 (2022) + C++17 | Steinberg ASIO SDK 2.3 |
| macOS | Xcode 16.2.0 | — |
| Linux | Clang 13 or GCC 10 | libportaudio19-dev |
| ESP32 | ESP-IDF compatible | — |

**Submodule dependency:** `modules/asio-standalone` must be initialized (`git submodule update --init --recursive`) — provides Asio (standalone, no Boost) for UDP networking and async I/O.

```cmake
# CMake integration
include($PATH_TO_LINK/AbletonLinkConfig.cmake)
target_link_libraries($YOUR_TARGET Ableton::Link)
```

---

### Behavioral Contract (Test Plan Summary)

The `TEST-PLAN.md` defines the required behavioral contract for Link- compliant apps. Key invariants that must hold:

| Test | Invariant |
|------|-----------|
| TEMPO-1 | Tempo changes propagate bidirectionally and keep all peers in sync |
| TEMPO-2 | Joining an existing session adopts the session's tempo (does not hijack) |
| TEMPO-3 | Loading a new song/document does not change the Link session tempo |
| TEMPO-4 | Full 20–999 BPM range supported (or lock to multiple/divisor) |
| BEATTIME-1 | Enable/disable Link causes no beat-time jump or audible discontinuity |
| BEATTIME-2 | New peers joining do not disrupt existing peers' beat time |
| STARTSTOPSTATE-1/2 | Start/stop commands propagate with quantization |
| AUDIOENGINE-1 | Output audio aligns to < **3 ms** tolerance with other Link peers |

---

### Integration Notes for `rhythm-vibe-mcp`

1. **Sub-beat-accurate timing source** — Link's `beatAtTime(hostTime + outputLatency, quantum)` provides a sub-millisecond resolved beat clock that can drive MIDI note scheduling, sample-accurate event quantization, and DAWproject `Warp` point generation.

2. **Tempo detection feedback loop** — `rhythm-vibe-mcp`'s tempo analysis output (BPM) can be **pushed into a Link session** via `SessionState::setTempo()`, and tempo changes from peer DAWs can be pulled via the tempo callback, creating a bidirectional sync.

3. **Quantized launch from generated content** — When `rhythm-vibe-mcp` generates a new pattern or MIDI sequence, `requestBeatAtTime(0, now(), 4.0)` ensures the pattern starts on the next 4-beat boundary in sync with a live Ableton Live or Studio One session.

4. **Phase export to DAWproject** — The Link session phase at a given moment (`phaseAtTime(t, quantum)`) provides the beat-position metadata needed to populate `Clip.time` and `Warp` anchor values in a DAWproject export.

5. **C API for Python integration** — The `abl_link` C extension (`abl_link.h` + `abl_link.cpp`) can be compiled to a shared library and wrapped with Python `ctypes` or `cffi`, enabling `rhythm-vibe-mcp`'s Python server to participate in a live Link session without a C++ build step in the main project.

6. **LinkAudio for live stem routing** — The `LinkAudio` extension enables direct peer-to-peer audio routing synchronized to the beat grid — e.g., `rhythm-vibe-mcp` could broadcast a generated backing track as a `LinkAudioSink` that any connected Link-enabled DAW can receive as a `LinkAudioSource`, all in phase.

---

## lmms

> **Repository origin:** `vendor/lmms/`  
> **Language:** C++17 / Qt 5–6  
> **License:** GPL-2.0  
> **Role in rhythm-vibe-mcp:** Reference implementation of a complete open-source DAW — oscillator, filter, envelope, note, effect-chain, and plugin hosting code that can be studied for algorithm extraction or cross-compiled for embedded DSP use.

### Overview

LMMS (Linux MultiMedia Studio) is a full-featured, cross-platform music production environment. Its source tree under `vendor/lmms/` is organized as:

```
include/          ~250 public C++ headers  (API surface, all algorithms declared here)
src/              implementation files
plugins/          ~55 instrument + effect subdirectories
data/             factory presets, sample maps, LFO shape data
tests/            unit + integration tests
```

The architecture separates three major subsystems:

| Subsystem | Purpose |
|-----------|---------|
| **Audio Engine** | Thread-safe render loop, FIFO, worker thread pool |
| **Song / Track / Clip model** | Qt-model-driven project data graph |
| **Plugin framework** | Instrument, Effect, LADSPA, LV2, VST2, Carla hosts |

---

### 1. Fundamental Types (`LmmsTypes.h`, `SampleFrame.h`)

**Type aliases** (all `float` unless noted):

| Alias | Type | Meaning |
|-------|------|---------|
| `sample_t` | `float` | single audio sample, normalized [-1, 1] |
| `int_sample_t` | `int16_t` | 16-bit PCM for output |
| `sample_rate_t` | `uint32_t` | Hz |
| `fpp_t` | `int32_t` | frames per processing period |
| `f_cnt_t` | `int32_t` | general frame count |
| `ch_cnt_t` | `int32_t` | channel count |

**`SampleFrame`** is the fundamental stereo interleaved unit — a value type wrapping `std::array<sample_t, 2>`:

```cpp
SampleFrame(sample_t left, sample_t right);
sample_t& left();  sample_t& right();

SampleFrame operator+(const SampleFrame&) const;
SampleFrame operator*(float)             const;
sample_t    sumOfSquaredAmplitudes()     const; // L² + R²
sample_t    average()                    const;
SampleFrame abs()                        const;
SampleFrame absMax(const SampleFrame&);         // per-channel peak
```

A processing period is an `SampleFrame*` array of length `framesPerPeriod` (default 256, range [32, 4096]).  
The de-facto output multiplier is `32767.0f` (OUTPUT_SAMPLE_MULTIPLIER), so the engine works internally in floating-point [-1, 1] and converts to int16 at the output stage.

Free-standing helpers for zero-fills, peak detection, and float-array interleave/de-interleave:

```cpp
void zeroSampleFrames(SampleFrame* buf, size_t frames);
SampleFrame getAbsPeakValues(SampleFrame* buf, size_t frames);
void copyToSampleFrames(SampleFrame* dst, const float* src, size_t frames);
void copyFromSampleFrames(float* dst, const SampleFrame* src, size_t frames);
```

---

### 2. Math & Utility Library (`lmms_math.h`, `lmms_constants.h`)

`lmms_math.h` is the single-header utility belt for all DSP code.  Key facilities:

#### Phase arithmetic
```cpp
inline auto fraction(std::floating_point auto x)    // x - trunc(x)  → [-1, 1)
inline auto absFraction(std::floating_point auto x) // x - floor(x)  → [0, 1) (normalized phase)
```

#### Pseudo-random noise (thread-local LCG, period 2^32)
```cpp
inline int fastRand();                  // [0, 32768)
template<T> T fastRandInc(T upper);    // inclusive upper bound, signed/unsigned/float overloads
inline bool oneIn(unsigned chance);    // true with probability 1/chance
```

#### dB / linear conversion
```cpp
inline float ampToDbfs(float amp);           // 20 * log10(amp)
inline float dbfsToAmp(float dbfs);          // 10^(dbfs/20)
inline float safeAmpToDbfs(float amp);       // handles 0.0 → -inf
inline float safeDbfsToAmp(float dbfs);      // handles -inf → 0.0
```

#### Scale mapping  
```cpp
inline float logToLinearScale(float min, float max, float value);  // exponential scaling (base e)
inline float linearToLogScale(float min, float max, float value);  // inverse
inline double fastPow(double a, double b);   // IEEE bit-trick approximation
```

#### SSE2 vector paths (compile-guarded `#ifdef __SSE2__`)
```cpp
inline __m128 fastExp( __m128 x);  // polynomial approximation, max rel-err 1.73e-3
inline __m128 fastLog( __m128 a);  // bit-manipulation + polynomial, max rel-err 7.9e-4
inline __m128 sse2Floor(__m128 x);
inline __m128 sse2Round(__m128 x);
inline __m128 sse2Abs (__m128 x);
```

#### `LinearMap<T>` — two-point affine mapping (y = a·x + b)

---

### 3. Interpolation Library (`interpolation.h`)

All functions are `inline float` header-only; all take normalized fractional position in [0, 1]:

| Function | Points | Algorithm |
|----------|--------|-----------|
| `hermiteInterpolate(x0,x1,x2,x3, t)` | 4 | Hermite cubic spline with velocity endpoints |
| `cubicInterpolate(v0,v1,v2,v3, x)` | 4 | Catmull-Rom / cubic spline |
| `cosinusInterpolate(v0,v1, x)` | 2 | Cosine blend: `0.5*(1-cos(π·x))` interpolant |
| `optimalInterpolate(v0,v1, x)` | 2 | Polynomial odd/even decomposition (optimal 2-pt) |
| `optimal4pInterpolate(v0…v3, x)` | 4 | Optimal 4-point, 3rd-order, centered at 0.5 |
| `lagrangeInterpolate(v0…v3, x)` | 4 | Lagrange polynomial |

These are used uniformly in oscillator wavetable lookup, user-wave sample playback, granular pitch shifting, and any sample-rate conversion that needs high-quality inter-sample estimation.

---

### 4. Audio Engine (`AudioEngine.h`)

The engine is a `QObject` singleton (`Engine::audioEngine()`) managing:

- **Buffer constants**: `MINIMUM_BUFFER_SIZE = 32`, `DEFAULT_BUFFER_SIZE = 256`, `MAXIMUM_BUFFER_SIZE = 4096`
- **Supported sample rates**: 44100, 48000, 88200, 96000, 192000 Hz

#### Four-stage rendering pipeline

Each period calls these private methods in order:

```
renderStageNoteSetup()    →  distribute Note/MIDI events to PlayHandles
renderStageInstruments()  →  dispatch PlayHandles to AudioEngineWorkerThreads (parallelized)
renderStageEffects()      →  apply per-AudioBusHandle EffectChains
renderStageMix()          →  sum AudioBusHandles into master output buffer, apply masterGain
```

Worker threads operate on slices of the `PlayHandleList` concurrently; the `RequestChangesGuard` RAII lock serializes any model mutation against the audio thread via `requestChangeInModel()` / `doneChangeInModel()` (backed by `std::recursive_mutex`).

#### FIFO render mode

A dedicated `fifoWriter : public QThread` can pre-render buffers into a `FifoBuffer<SampleFrame*>` to decouple the audio interrupt latency from render jitter — used when `needs_fifo = true` (typically non-realtime project export via `ProjectRenderer`).

#### Input buffering

Double-buffered input (index alternated on each period) isolates writes from the current read:

```cpp
SampleFrame* m_inputBuffer[2];
f_cnt_t m_inputBufferFrames[2];
int m_inputBufferRead, m_inputBufferWrite;
```

#### `AudioEngineProfiler`

Tracks CPU load with `DetailType` breakdown (instruments, effects, mixing), exposed as integer percent via `cpuLoad()`.

---

### 5. Oscillator Engine (`Oscillator.h`)

`class Oscillator` is the template voice oscillator used by TripleOscillator and many other plugins.

#### Wave shapes (enum `WaveShape`)

| Shape | Algorithm |
|-------|-----------|
| `Sine` | Direct: `sin(2π·sample)` |
| `Triangle` | Piecewise linear over [0, 0.25, 0.75, 1] fractional phase |
| `Saw` | `-1 + absFraction(sample) * 2` |
| `Square` | `absFraction(sample) > 0.5 ? -1 : 1` |
| `MoogSaw` | Bipolar ramp with reversed slope at 0.5 |
| `Exponential` | `–1 + 8·ph²` (parabolic, mirrored at 0.5) |
| `WhiteNoise` | Thread-local LCG via `fastRandInc(-1, 1)` |
| `UserDefined` | Linear interp into `SampleBuffer`; AA variant uses generated wavetable |

#### Band-limited wavetable system (FFTW3)

To prevent aliasing at high frequencies, Triangle, Saw, and Square use pre-generated multi-band wavetables stored in:

```cpp
static sample_t s_waveTables[NumWaveShapeTables]
                             [WAVE_TABLES_PER_WAVEFORM_COUNT]
                             [WAVETABLE_LENGTH];
```

Band selection formula (based on MIDI key):

```cpp
int band = ceil(12 * log2(freq / 440)) / SEMITONES_PER_TABLE;
// clamped to [1, WAVE_TABLES_PER_WAVEFORM_COUNT-1]
```

`waveTableInit()` generates bands via `fftwf_plan` forward + inverse FFT, zeroing harmonics above Nyquist for each band.  
All wavetable lookups use `std::lerp` between adjacent table samples at `control.f1 / control.f2`.

#### Modulation algorithms (enum `ModulationAlgo`)

| Mode | Method |
|------|--------|
| `PhaseModulation` | Sub-osc output added to phase offset before sample fetch |
| `AmplitudeModulation` | Sub-osc output multiplies main osc amplitude |
| `SignalMix` | Sub and main outputs summed |
| `SynchronizedBySubOsc` | Hard sync — resets main osc phase when sub osc crosses zero |
| `FrequencyModulation` | True FM: sub-osc output added to frequency coefficient |

Each mode × wave shape has a dedicated template specialization `updatePM<WaveShape W>()`, `updateAM<WaveShape W>()`, etc., compiled out as separate functions for maximum performance.

#### UserDefined anti-alias wavetable

`generateAntiAliasUserWaveTable(const SampleBuffer*)` takes an arbitrary waveform buffer and produces a band-limited version via the same FFT pipeline used for built-in shapes.

---

### 6. Filter Library (`BasicFilters.h`)

Header-only template library; primary class is `BasicFilters<ch_cnt_t CHANNELS>`.  
Also exposes `BiQuad<CHANNELS>`, `OnePole<CHANNELS>`, and `LinkwitzRiley<CHANNELS>` as separate reusable primitives.

#### Filter types (enum `FilterType`)

| Type | Algorithm |
|------|-----------|
| `LowPass` / `HiPass` / `BandPass_CSG` / `BandPass_CZPG` / `Notch` / `AllPass` | Standard RBJ biquad (transposed Direct Form II via `BiQuad`) |
| `Moog` | 4-pole Moog ladder: 4× cascaded bilinear one-poles with feedback coefficient `r`, soft-clip to ±10, cubic limiter on output: `y4 - y4³/6` |
| `DoubleMoog` | Two Moog ladders in series |
| `Tripole` | 3-pole Moog variant with 4× oversampling; input linearly interpolated across sub-samples; output averaged |
| `Lowpass_RC12` / `Bandpass_RC12` / `Highpass_RC12` | Analog RC integrator simulation (S. Fendt 1998), 4× oversampled, 12 dB/oct |
| `Lowpass_RC24` / `Bandpass_RC24` / `Highpass_RC24` | Two cascaded RC stages, 4× oversampled, 24 dB/oct |
| `Lowpass_SV` / `Bandpass_SV` / `Highpass_SV` / `Notch_SV` | Hal Chamberlin state-variable filter (2× oversampled): `lp += f·bp; hp = in - lp - q·bp; bp += f·hp` — second 2-pole stage chained for 4-pole output |
| `Formantfilter` | 6-formant vowel filter (vf arrays) with 4× oversampling |
| `FastFormant` | Same without oversampling |

Also included as a standalone class:

**`LinkwitzRiley<CHANNELS>`** — 4th-order (LR4) crossover filter:  
Bilinear-transform design computing wc⁴ / k⁴ coefficients with sqrt(2) intermediate terms; `setLowpass(freq)` / `setHighpass(freq)` produce perfect-reconstruction pair (LP + HP sums to allpass).

**`BiQuad<CHANNELS>`** — transposed Direct Form II biquad:
```cpp
out = z1 + b0·in;  z1 = b1·in + z2 - a1·out;  z2 = b2·in - a2·out;
```

**`OnePole<CHANNELS>`** — single-pole smoother: `z1 = s·a0 + z1·b1` (with silence gate).

---

### 7. Envelope & LFO (`EnvelopeAndLfoParameters.h`)

A single `EnvelopeAndLfoParameters` object holds both the DAHDSR envelope and an LFO, allowing per-parameter modulation.

#### Envelope — PAHD+R (Pre-delay, Attack, Hold, Decay, Sustain, Release)

Precomputed sample arrays `m_pahdEnv[]` and `m_rEnv[]` are populated via `updateSampleVars()`.  
Shape uses `expKnobVal(val) = val * |val|` — a symmetric cubic response mapping knob position to exponential curve time.

`fillLevel(float* buf, f_cnt_t frame, f_cnt_t release_begin, fpp_t frames)` writes the level multiplier stream.

#### LFO shapes (enum `LfoShape`)

```
SineWave, TriangleWave, SawWave, SquareWave, UserDefinedWave, RandomWave
```

LFO speed is controlled via `TempoSyncKnobModel` — can be free-running Hz or locked to project tempo as a note fraction (1/1 to 1/192).  
Pre-delay and attack ramp are applied before the oscillation output is used as a modulation source.  
`LfoInstances` singleton coordinates global trigger and reset of all LFOs at transport start.

---

### 8. Effect & EffectChain (`Effect.h`, `EffectChain.h`)

`Effect` extends `Plugin` and forms the base for all audio processors.

#### Processing flow

```cpp
bool Effect::processAudioBuffer(SampleFrame* buf, fpp_t frames)
```

1. If disabled, `processBypassedImpl()` is called (optional — default no-op).
2. `processImpl()` is called; returns one of:
   - `Continue` — unconditionally keep running
   - `ContinueIfNotQuiet` — compute RMS; if below silence threshold for `timeout()` periods, enter sleep
   - `Sleep` — do not process
3. Wet/dry mix: `out = wet·processed + (1–wet)·original`.
4. Auto-quit: after `autoQuitModel` ms of silence, `m_running = false`; reactivated by non-silent input.

`EffectChain` chains N `Effect` instances; applies them in list order per `fpp_t` period.

#### Plugin format bridges

| Class | Protocol |
|-------|---------|
| `LadspaEffect` | Runs LADSPA descriptors; discovers via `LadspaManager` path scan |
| `Lv2Effect` / `Lv2Instrument` | LV2 host via `Lv2Manager` (lilv-based) |
| `VstEffect` / `VstInstrument` | VST2 bridge via `VestigeInstrumentPlugin` (vestige header) |
| `CarlaInstrument` / `CarlaEffect` | Carla plugin host — supports VST3, AU, CLAP, LV2 through Carla's patchbay/rack |

---

### 9. Notable Built-in Instrument Plugins

| Plugin dir | Synthesis paradigm |
|------------|-------------------|
| `TripleOscillator` | 3× `Oscillator` with all 5 modulation modes, per-osc tuning/pan/vol, unison detune |
| `BitInvader` | Drawn waveform (user wavetable), bit-depth reduction, interpolation on/off |
| `Lb302` | Roland TB-303 emulation; analog ladder resonance approximation; accent/slide per-note |
| `Monstro` | 3 oscillators + 2 envelopes + 2 LFOs + 2 arp/chord modules; 56 modulation targets |
| `Watsyn` | 4-operator wavetable FM with A×B, A+B, A, and mixed routing modes |
| `Xpressive` | Spectral morphing wavetable synth with 2D morph grid; FFTW-based resynthesis |
| `Vibed` | Physical modelling of vibrating string; Karplus–Strong variant with N partials |
| `Organic` | Additive synthesis with harmonic wheel GUI (Hammond organ emulation) |
| `Nes` | NES APU emulation — pulse 1/2 (duty cycle), triangle, noise, DPCM |
| `FreeBoy` | Game Boy DMG APU emulation — 2× square, wave table, LFSR noise |
| `Sfxr` | Procedural SFX synthesizer (SFXR/BFXR primitives) |
| `Sid` | MOS SID 6581/8580 chip emulation |
| `OpulenZ` | OPL2/OPL3 FM synthesis (Yamaha YM3812 / YMF262) |
| `ZynAddSubFx` | Full ZynAddSubFX engine embedded; Additive + Subtractive + PADsynth modes |
| `GigPlayer` | GigaSampler (.gig) sample player |
| `Sf2Player` | SoundFont 2 player |
| `Stk` | Physical models from Perry Cook's STK (blowhole, clarinet, bowed string, etc.) |

---

### 10. Notable Built-in Effect Plugins

#### ReverbSC (`plugins/ReverbSC/`)

Port of the Csound `reverbsc` opcode (Sean Costello / Istvan Varga, 1999/2005) via Soundpipe.

Architecture: **8 parallel modulated delay lines** fed in a feedback network:

```c
static const SPFLOAT reverbParams[8][4] = {
    { 2473/sr, 0.0010, 3.100, 1966  },  // [delay_seconds, rand_variation, rand_freq, rand_seed]
    { 2767/sr, 0.0011, 3.500, 29491 },
    { 3217/sr, 0.0017, 1.110, 22937 },
    ...
};
```

Each delay line has:
- A fixed nominal delay (prime-number milliseconds to avoid metallic coloring)
- A random pitch-modulated variation (`iPitchMod` controls depth); delay length oscillates at its own `randLine_cnt` frequency
- A lowpass one-pole filter at `lpfreq` controlling `dampFact` (high-frequency decay)
- Fixed-point fractional read position for sub-sample interpolation (`DELAYPOS_SHIFT = 28`, scale `0x10000000`)

Feedback coefficient `p->feedback` (default 0.97) controls RT60.  
Output gain: `0.35f × Σ delay_outputs` with JP (Jonos/Paynter) mixing matrix scale `0.25`.  
`dcblock.c` provides a simple DC-blocking highpass before output.

#### GranularPitchShifter (`plugins/GranularPitchShifter/`)

Streaming granular pitch shifter (2024, Lost Robot).

- **Ring buffer** (`m_ringBuf`): incoming audio continuously written; grains read at different rates
- **Grain struct**: holds `readPoint[2]`, `phaseSpeed[2]`, `grainSpeed[2]`, `phase` — two independent L/R read heads allow stereo width control via `m_glide`
- **Read speed** = `pitch_ratio` (> 1 = pitch up, < 1 = pitch down); phase wraps to produce continuous stream of overlapping grains
- **Window function**: `cosHalfWindowApprox(x, k)` — approximation of `(B + x)²` where `B = x(1–x)(1 + k·x(1–x))`, k interpolated between equal-gain (k≈–6) and equal-power (k≈1) via `cosWindowApproxK(p)` (Signalsmith's cheap-energy crossfade)
- **Hermite interpolation**: `getHermiteSample(double index, ch)` reads from ring buffer with wrapping; uses 4-point `hermiteInterpolate` for sub-sample accuracy
- **Pre-filter**: 2nd-order SVF lowpass at `PrefilterBandwidth × Nyquist` (0.96) using linearized bilinear transform for anti-aliasing before writing to ring buffer
- **Safety saturator**: soft-clip `f(x) = (|x| – SatuSafeVol)/(1 + (|x| – SatuSafeVol)·SatuStrength) + SatuSafeVol` (only activates above 16× nominal)
- **DC removal**: `DcRemovalHz = 7 Hz` one-pole highpass applied to output
- **Sample rate update**: via `sampleRateNeedsUpdate()` flag pattern (deferred recompute)

#### Other effects (summary)

| Plugin | Algorithm summary |
|--------|------------------|
| `Delay` | Stereo delay with feedback, tempo-sync time, ping-pong mode |
| `MultitapEcho` | Up to N taps with individual delay/gain/pan, all-pass diffuser option |
| `Flanger` | LFO-modulated delay + comb filter; stereo spread via phase offset |
| `Dispersion` | Phase dispersion (allpass cascade); simulates material group delay |
| `Eq` / `CrossoverEQ` | Parametric EQ using RBJ biquads; Linkwitz–Riley crossover |
| `DualFilter` | Two serial `BasicFilters` with independent cutoff/resonance + morph between them |
| `Compressor` | Peak/RMS with lookahead, knee, stereo-link |
| `LOMM` | LKJB LOMM mastering limiter |
| `DynamicsProcessor` | Full dynamics chain: gate, comp, expander with custom transfer curve |
| `BassBooster` | Shelf + low-freq harmonic saturation |
| `Bitcrush` | Bit depth reduction + sample-rate decimation |
| `WaveShaper` | Arbitrary transfer function via drawn curve |
| `StereoEnhancer` | Mid/side width manipulation |
| `StereoMatrix` | Arbitrary L/R routing matrix (M/S encode/decode, swaps, mono sums) |
| `SpectrumAnalyzer` | FFT display (FFTW3 back-end); not an audio processor |
| `Vectorscope` | XY phase scope display |

---

### 11. Note and Song Data Model

#### `Note` (`Note.h`)

A `Note` is a timed MIDI-note-like event with:
```cpp
TimePos pos();        // position in ticks (192 ticks/quarter note default)
TimePos length();     // duration in ticks
int  key();           // MIDI key 0-127 (Key::C…H × Octave)
volume_t volume();    // 0–200 (default 100)
panning_t panning();  // -100…+100
```

`Note::Type`: `Regular` (piano-roll) or `Step` (beat sequencer).  
Per-note detuning automation is supported via a `DetuningHelper` → `AutomationClip` pointer.

Key constants:
```cpp
const int NumKeys    = 128;
const int DefaultKey = Octave_4 + Key::A;  // A4 = MIDI 69
const float DefaultBaseFreq = 440.f;
const float MaxDetuning = 5 * 12.0f;       // ± 5 octaves
```

#### Project graph

```
Song
 └─ Track[]
     ├─ InstrumentTrack   → owns Instrument + EffectChain + EnvelopeAndLfoParameters
     │   └─ MidiClip[]    → holds Note[] sorted by position
     ├─ BeatTrack         → Step-grid pattern of Notes
     ├─ SampleTrack       → playback of audio file clips
     └─ AutomationTrack   → AutomationClip (breakpoint-based) → AutomatableModel target
```

`AutomatableModel` is the base for every knob/slider value in the engine; it carries min/max/default/step and emits change signals used by both the GUI and the automation system.

---

### 12. Integration Notes for `rhythm-vibe-mcp`

| Use-case | Relevant lmms code |
|----------|--------------------|
| **Algorithm extraction** | `BasicFilters.h` provides 22 production-quality filter algorithms  header-only; linkable without Qt by removing the `#include "lmms_constants.h"` dependency |
| **Band-limited oscillator** | `Oscillator.h` + `OscillatorConstants.h` + FFTW3: the multi-band wavetable system is self-contained; `waveTableInit()` / `generateAntiAliasUserWaveTable()` can be called stand-alone |
| **Interpolation** | `interpolation.h` is pure C++17 with no dependencies — 6 algorithms from linear to Hermite cubic; directly importable |
| **dB/log utilities** | `lmms_math.h` `ampToDbfs`, `dbfsToAmp`, `fastPow`, SSE2 paths — all header-only inline |
| **Envelope shapes** | `EnvelopeAndLfoParameters::expKnobVal()` and the PAHD/R precompute loop are extractable for use in rhythm-vibe-mcp's own amplitude envelopes |
| **Granular pitch shift** | `GranularPitchShifterEffect` is an end-to-end reference; the ring-buffer + Hermite + cosine-power window design covers the full quality pipeline |
| **Reverb** | `revsc.c` is ANSI C with no dependencies; the 8-delay-line feedback network + modulation + damping LP is a complete, standalone reverb unit |
| **Plugin hosting** | `LadspaManager`, `Lv2Manager`, `CarlaInstrument`/`CarlaEffect` headers define the host interface needed to load third-party processors if rhythm-vibe-mcp gains a plugin layer |

---

## rubberband

> **Repository origin:** `vendor/rubberband/`  
> **Version:** 4.0.0 (API v3.0)  
> **Language:** C++14, ANSI C (KissFFT / Speex resampler bundled)  
> **License:** GPL-2.0 (commercial licence available)  
> **Author:** Chris Cannam / Particular Programs Ltd  
> **Role in rhythm-vibe-mcp:** The definitive open-source high-quality time-stretching and pitch-shifting pipeline — directly usable for tempo manipulation of generated audio without affecting pitch, or pitch transposition without affecting tempo.

### Overview

Rubber Band Library performs independent time-stretching and pitch-shifting of audio via a **Phase Vocoder Time-Scale Modification (PV-TSM)** approach. Two complete engines are provided:

| Engine | Alias | CPU cost | Best for |
|--------|-------|----------|---------|
| **R2** | Faster | Low | Real-time, simple material, percussion, legacy compat |
| **R3** | Finer | High (3–5× R2) | Complex mixes, vocals, bass-heavy material, studio quality |

Both engines expose the identical `RubberBandStretcher` C++ API and the `rubberband-c.h` C ABI.

---

### 1. Public API (`rubberband/RubberBandStretcher.h`)

#### Construction

```cpp
RubberBandStretcher(size_t sampleRate,
                    size_t channels,
                    Options options = DefaultOptions,
                    double initialTimeRatio = 1.0,
                    double initialPitchScale = 1.0);
```

`Options` is a bitmask selecting engine, mode, and tuning flags (see §2).

#### Two processing modes

**Offline mode** (default `OptionProcessOffline`):
1. Pass all audio through `study(input, n, finalFlag)` — builds stretch profile
2. Pass all audio through `process(input, n, finalFlag)` — stretches
3. Retrieve output via `retrieve(output, n)` — returns available frames

**Real-time mode** (`OptionProcessRealTime`):
- Single streaming pass: `process()` → `retrieve()`, no study phase
- `getSamplesRequired()` tells you how many input samples to feed per period
- `setTimeRatio()` / `setPitchScale()` can be changed at any time (RT-safe)
- RT-safe: no allocation, no locking during normal processing

#### Key methods

```cpp
void  setTimeRatio(double ratio);       // > 1 = slower; < 1 = faster
void  setPitchScale(double scale);      // > 1 = higher; < 1 = lower; semitones = pow(2, semis/12)
void  setFormantScale(double scale);    // independent formant envelope scaling (R3+formant option)

size_t getSamplesRequired() const;      // how many input frames to feed next
int    available() const;               // how many output frames ready
size_t retrieve(float **output, size_t frames) const;

size_t getPreferredStartPad() const;    // recommended silence to prepend
size_t getStartDelay() const;           // frames of latency to discard from output start
```

#### `OptionChannelsTogether` (stereo M/S mode)

When set, two-channel input is decoded to Mid/Side before processing and re-encoded on output. This maximises centre-image clarity and mono compatibility at the cost of slightly reduced per-channel detail. In R3 this also provides tighter inter-channel phase lock for low-frequency content.

#### `RubberBandLiveShifter` — pitch-only, minimal latency

A simpler class exposing only pitch shifting (no time stretch) optimised for minimum latency:

```cpp
RubberBandLiveShifter(size_t sampleRate, size_t channels, Options = DefaultOptions);
void  setPitchScale(double scale);
size_t getStartDelay() const;
void  shift(const float *const *input, float *const *output, size_t count);
// Note: shift() is blocking and does not use a retrieve() call
```

---

### 2. Option Flags

| Flag group | Key values | Notes |
|-----------|-----------|-------|
| **Engine** | `OptionEngineFaster` (0x0), `OptionEngineFiner` (0x20000000) | Fixed at construction |
| **Mode** | `OptionProcessOffline` (0x0), `OptionProcessRealTime` (0x1) | Fixed at construction |
| **Transients** (R2 only) | `OptionTransientsCrisp` / `Mixed` / `Smooth` | Crisp = phase reset at transient peaks |
| **Detector** (R2 only) | `OptionDetectorCompound` / `Percussive` / `Soft` | Selects transient curve type |
| **Phase** (R2 only) | `OptionPhaseLaminar` / `Independent` | Laminar = neighbour-coherent phase propagation |
| **Window** | `OptionWindowStandard` / `Short` / `Long` | Short enables single-band R3 (much faster) |
| **Smoothing** (R2 only) | `OptionSmoothingOff` / `On` | Time-domain smoothing via window-presum FFT |
| **Formant** | `OptionFormantShifted` / `Preserved` | Preserved = cepstral envelope extraction+restoration |
| **Pitch** | `OptionPitchHighSpeed` / `HighQuality` / `HighConsistency` | Selects resampler placement and allows dynamic pitch change |
| **Channels** | `OptionChannelsApart` / `Together` | Together = M/S stereo processing |

Preset: `PercussiveOptions = OptionWindowShort | OptionPhaseIndependent`.

---

### 3. R2 (Faster) Engine — Phase Vocoder with Transient Detection

The R2 engine (`src/faster/`) is the classic PVOC-TSM pipeline used since Rubber Band v1:

#### Per-channel processing loop

```
inbuf → [analysis window × Hann] → FFT → polar form
       → transient/phase decision
       → phase propagation → IFFT × synthesis window → OLA → outbuf
```

#### Window and FFT sizing

Analysis window size is calculated in `R2Stretcher::calculateSizes()` from the time ratio. The default size at 44100 Hz is typically 2048–8192 samples. Short mode uses 512–1024; long mode uses 8192–16384.

**`cutShiftAndFold()`** applies the window, then folds the signal so DC is at the centre — this is the "fftshift" step before `FFT::forward()`.

#### Transient detection — `CompoundAudioCurve` / `AudioCurveCalculator`

The `StretchCalculator` runs on the study-pass magnitudes and builds a vector of output increments. Three curve calculators can contribute:

| Calculator | Signal measured |
|-----------|----------------|
| `PercussiveAudioCurve` | Frame-to-frame spectral flux (sum of magnitude increases across bins) → transient when flux exceeds adaptive threshold |
| `HighFrequencyAudioCurve` | Energy-weighted frequency centroid rise → detects broadband high-frequency onsets |
| `SilentAudioCurve` | Below-threshold silence detector — suppresses false transient detections in silence |

`CompoundAudioCurve` combines these in a weighted sum (`OptionDetectorCompound`) or delegates to `PercussiveAudioCurve` alone (`OptionDetectorPercussive`) or `HighFrequencyAudioCurve` alone (`OptionDetectorSoft`).

#### Phase propagation modes

**Laminar phase** (`OptionPhaseLaminar`): for each frequency bin, the predicted phase advance is adjusted by the phase residual (deviation from the expected frequency), and this adjusted phase is then propagated to neighbouring bins that share the same spectral peak — preserving phase relationships across partials of a harmonic note.

**Independent phase** (`OptionPhaseIndependent`): each bin updated with `prevOutPhase + ratio × (omega + error)` independently. Slightly phasier but simpler.

**Phase reset** (`OptionTransientsCrisp`): at detected transient peaks, output phases are immediately set to the current input phases, discarding all accumulated phase shift. This preserves attack clarity but can cause brief interruptions in co-occurring sustained tones.

---

### 4. R3 (Finer) Engine — Multi-Resolution Guided Phase Vocoder

The R3 engine (`src/finer/`) introduces a fundamentally different approach: rather than a single FFT size, it simultaneously runs **three FFT sizes** chosen to give the best time-frequency trade-off across the audible spectrum.

#### Multi-resolution band structure

At 44100/48000 Hz, the three bands are:

| Band | FFT size | Frequency range | Characteristic |
|------|----------|----------------|----------------|
| Long (`longestFftSize`) | ~3000 samples | 0 – ~700 Hz | Best frequency resolution for bass/fundamentals |
| Classification (`classificationFftSize`) | ~1500 samples | 0 – Nyquist | General purpose; used for classification |
| Short (`shortestFftSize`) | ~750 samples | ~4800 Hz – Nyquist | Best time resolution for high-frequency transients |

In **OptionWindowShort** (single-window mode) all three bands collapse to the classification FFT size — faster but lower quality.

`Guide::Configuration` sets these sizes on construction: `longestFftSize = 2 × classificationFftSize`, `shortestFftSize = classificationFftSize / 2`. The `updateGuidance()` method dynamically adjusts the frequency boundaries `lower` (default ~700 Hz, range 500–1100) and `higher` (default ~4800 Hz, range 4000–7000) by `descendToValley()` — descending the magnitude spectrum from the current boundary to the nearest local minimum, so band boundaries follow natural spectral valleys.

#### Per-frame data structures

Each channel carries:
- `ChannelData` — per-channel state: ring buffers, classification arrays, segmentation results, formant data
- `ChannelScaleData` (one per FFT size) — time-domain buffer, `real[]`, `imag[]`, `mag[]`, `phase[]`, `advancedPhase[]`, `prevMag[]`, `pendingKick[]`, `accumulator[]` (OLA output)
- `ScaleData` (shared across channels per FFT size) — `FFT`, `analysisWindow`, `synthesisWindow`, `windowScaleFactor`, `GuidedPhaseAdvance`

The analysis window for R3 is always **NiemitaloForwardWindow** (an asymmetric window proposed by Olli Niemitalo that is shorter on the causal end) with a complementary NiemitaloReverseWindow for synthesis — this pair provides a lower-latency, near-perfect reconstruction window that is better suited to the multi-resolution OLA scheme than symmetric windows.

#### BinClassifier — per-bin Harmonic/Percussive/Residual labelling

`BinClassifier` implements a **moving-median HPSS** (Harmonic/Percussive Source Separation) online classifier:

```
For each new frame:
  hf[bin] = MovingMedian(mag[bin])  over time (horizontal, length ~15 frames)
  vf[bin] = MovingMedian(mag[0..N]) over frequency (vertical, length ~7 bins) from lag-delayed frame

  if hf[i] / vf[i] > harmonicThreshold   → Harmonic  (stable over time, narrow in frequency)
  elif vf[i] / hf[i] > percussiveThreshold → Percussive (broadband, transient in time)
  else                                     → Residual
```

The horizontal filter has a lag (`horizontalFilterLag`) to align time-domain features with frequency-domain features, implemented via a pointer-swap queue of `process_t*` arrays.

#### BinSegmenter — spectrum-level segmentation

`BinSegmenter` aggregates the per-bin classifications from `BinClassifier` into frequency boundaries:

```
Segmentation {
    double percussiveBelow;   // highest Hz below which bins are predominantly Percussive
    double percussiveAbove;   // lowest Hz above which bins are predominantly Percussive
    double residualAbove;     // lowest Hz above which bins are predominantly Residual
}
```

These boundaries drive kick detection in `Guide::updateGuidance()`:
- `kick`: triggered when `percussiveBelow > 40 Hz` this frame AND `< 40 Hz` previous frame AND `checkPotentialKick()` confirms magnitude increase
- `futureKick` (preKick): kick predicted in the next frame — allows the engine to prepare phase freeze before the attack arrives

#### Guide — per-frame processing decisions

`Guide::updateGuidance()` reads the segmentation and produces a `Guidance` struct:

```cpp
struct Guidance {
    FftBand      fftBands[3];          // which FFT size to use for each frequency range
    PhaseLockBand phaseLockBands[4];   // peak neighbourhood size p, and beta for each freq band
    Range kick;       // reset phases here on kick onset
    Range preKick;    // freeze phases here before kick arrives
    Range highUnlocked; // allow independent phase update (residual content)
    Range phaseReset;   // phase reset for sudden spectral changes
    Range channelLock;  // use greatest-magnitude channel's peak assignments for both channels
};
```

The `betaFor(f, ratio)` function computes PhaseLock strength β: at low ratios (near-unity), β → 1 (tight locking); at extreme ratios, β decreases to allow more phase freedom.

#### GuidedPhaseAdvance — the core phase update rule

`GuidedPhaseAdvance::advance()` computes the output phase for every bin, per frame, per channel:

**Step 1: Unlocked phase estimate** (standard PVOC formula)
```
omega  = 2π × inhop × bin / fftSize          // expected phase advance for this bin
error  = princarg(phase[c][i] - prevIn[c][i] - omega)   // deviation from expected
unlocked[c][i] = prevOut[c][i] + ratio × (omega + error)  // advance scaled by time ratio
```

**Step 2: Peak picking**  
For each `PhaseLockBand`, `findNearestAndNextPeaks(mag, startBin, count, p, peaks[])` labels every bin with its nearest spectral peak (within neighbourhood of ±p). Previous-frame peak labels are also computed for tracking.

**Step 3: Channel synchronisation** (`channelLock` range)  
For stereo with `OptionChannelsTogether`, the bin's dominant channel (by magnitude) is identified; that channel's output phase is used as the reference for the other channel — maintaining the stereo image.

**Step 4: Phase decision per bin**  
```
if inRange(bin, phaseReset) or inRange(bin, kick):
    outPhase = inputPhase[c][i]                  // hard reset: copy analysis phase
elif inRange(bin, preKick):
    outPhase = prevOut[c][i]                     // freeze: hold phase until kick lands
elif inRange(bin, highUnlocked):
    outPhase = unlocked[c][i]                    // independent update (residual)
else:
    peak = currentPeaks[c][i]
    prevPeak = prevPeaks[gc][i]   // gc = greatest-magnitude channel for channelLock
    beta = phaseLockBand.beta
    locked = unlocked[gc][peak] + (inputPhase[c][i] - inputPhase[gc][peak])  // track peak
    outPhase = beta × locked + (1 - beta) × unlocked[c][i]    // blend locked vs free
```

This β-weighted blend is the key innovation of R3: it provides **soft phase locking** — tight for harmonic content (β→1), looser for high frequencies (β→0) where phase coherence matters less.

#### Formant preservation (OptionFormantPreserved)

Formant shape is extracted via **cepstral liftering**:
1. Compute `log(mag)` spectrum
2. IFFT → real cepstrum in `FormantData::cepstra[]`
3. Zero all cepstral coefficients above a low-quefrency threshold (lifter)
4. FFT back → log spectral envelope in `FormantData::envelope[]`
5. On output: divide by input envelope (shift formants out), multiply back by envelope at original pitch (restore formant shape)

`setFormantScale(scale)` allows formant frequency to be shifted independently of pitch — e.g., pitch-shift a voice up without raising the formant peak (avoiding the "chipmunk" effect).

#### Resampler placement for pitch shifting

The time ratio and pitch scale are decoupled via resampling. `areWeResampling(before, after)` decides placement:

| Mode | Pitch > 1 | Pitch < 1 |
|------|-----------|-----------|
| RT `OptionPitchHighSpeed` | resample *before* (downsample input, then stretch back) | resample *after* |
| RT `OptionPitchHighQuality` | resample *after* | resample *before* (upsample input) |
| RT `OptionPitchHighConsistency` | always resample *after* | always resample *after* |
| Offline (any) | always resample *after* | always resample *after* |

`HighConsistency` is required for dynamic pitch changes without discontinuities (e.g., vibrato, glide).

The `Resampler` class wraps either **libsamplerate** (if available), **SpeexResampler** (`src/ext/speex/resample.c`), or `BQResampler` (built-in sinc-based resampler in `src/common/`).

---

### 5. Window Functions (`src/common/Window.h`)

```cpp
enum WindowType {
    RectangularWindow,      // 0.5 gain (for OLA compatibility)
    BartlettWindow,         // linear taper
    HammingWindow,          // cosine: [0.54, 0.46, 0, 0]
    HannWindow,             // cosine: [0.50, 0.50, 0, 0]
    BlackmanWindow,         // cosine: [0.42, 0.50, 0.08, 0]
    GaussianWindow,         // exp(-(n / (N/2/3))^2 × ln(2))
    ParzenWindow,           // piecewise cubic B-spline
    NuttallWindow,          // 4-term cosine: [0.3636, 0.4892, 0.1366, 0.0106]
    BlackmanHarrisWindow,   // 4-term cosine: [0.3588, 0.4883, 0.1413, 0.0117]
    NiemitaloForwardWindow, // asymmetric (short causal side) — used in R3 analysis
    NiemitaloReverseWindow  // mirror of above — used in R3 synthesis
};
```

`Window<T>` provides `cut(block)` (multiply in-place), `cut(src, dst)`, `cutAndAdd(src, dst)` (OLA add), and `add(dst, scale)` for synthesis windowing. All use the `v_multiply` / `v_multiply_and_add` SIMD-dispatched vector ops in `VectorOps.h`.

---

### 6. FFT Backend (`src/common/FFT.h`)

The `FFT` class dispatches to the best available backend at compile time:

| Priority | Backend | Condition |
|----------|---------|-----------|
| 1 | Intel IPP | `HAVE_IPP` |
| 2 | FFTW3 (float) | `HAVE_FFTW3F` |
| 3 | SLEEF | `HAVE_SLEEF` |
| 4 | vDSP (Accelerate) | macOS/iOS |
| 5 | KissFFT | bundled fallback (`src/ext/kissfft/`) |

API:
```cpp
FFT fft(fftSize);
fft.forward(realIn, realOut, imagOut);     // R→2C
fft.forwardPolar(realIn, magOut, phaseOut);
fft.inverse(realIn, imagIn, realOut);      // 2C→R
fft.inversePolar(magIn, phaseIn, realOut);
```

`VectorOpsComplex` provides vectorised Cartesian↔polar bulk conversions (`v_cartesian_to_polar`, `v_cartesian_to_magnitudes`, etc.) with SSE2/NEON/vDSP dispatch.

---

### 7. StretchCalculator — Offline Hop Schedule

In offline mode, `StretchCalculator` (`src/common/StretchCalculator.cpp`) pre-computes the per-frame output hop sequence:

1. Run all audio through the transient detector; produce a `df[]` (detection function) array
2. Identify hard transient frames (peaks in `df[]` above adaptive threshold)
3. Between adjacent transients, apply uniform time stretching: `outhop = inhop × ratio`
4. At transients: pin an output frame exactly at the transient position (`exact-time-point`), adjusting the surrounding hops to compensate
5. `setKeyFrameMap(map<inputFrame, outputFrame>)` provides user-specified synchronisation points that override the automatic schedule

The result is a vector of `{ phaseIncrement, shiftIncrement, phaseReset }` triples consumed by R2's per-channel processing loop.

---

### 8. Integration Notes for `rhythm-vibe-mcp`

| Use-case | API / files |
|----------|------------|
| **Tempo change (offline)** | `OptionProcessOffline | OptionEngineFiner`; `study()` + `process()` + `retrieve()`; set `setTimeRatio(targetBPM / sourceBPM)`. Add `getPreferredStartPad()` frames of silence before feeding. |
| **Pitch transposition** | `setPitchScale(pow(2.0, semitones / 12.0))`; with `OptionFormantPreserved` for natural-sounding vocal pitch shifts |
| **Real-time pitch shift** | `OptionProcessRealTime | OptionPitchHighConsistency`; feed `getSamplesRequired()` frames per call; discard `getStartDelay()` frames at startup |
| **Live pitch-only** | `RubberBandLiveShifter`; `shift(in, out, count)` blocking call per period |
| **Extracting the resampler** | `src/common/Resampler.h` wraps Speex (bundled, BSD) — usable stand-alone for sample-rate conversion in any audio pipeline |
| **Extracting the window** | `src/common/Window.h` is header-only (only `VectorOps.h` dependency); provides 11 window types with `cut()` / `cutAndAdd()` OLA helpers |
| **Extracting HPSS** | `BinClassifier.h` + `BinSegmenter.h` can be used stand-alone for real-time harmonic/percussive separation given a magnitude spectrogram |

---

## stargate

> **Repository origin:** `vendor/stargate/`  
> **Language:** C (engine) + Python (GUI / scripting)  
> **License:** GPL-3.0  
> **Role in rhythm-vibe-mcp:** A complete, CPU-minimal open-source DAW. Its ANSI C `audiodsp` library provides a highly portable, dependency-light suite of production-quality DSP modules — oscillators, filters, envelopes, dynamics, reverb, chorus — that are extractable as-is for embedded or server-side audio processing.

### Overview

Stargate is a pattern-based DAW targeting extreme CPU efficiency ("runs on a Raspberry Pi 4 / 15-year-old laptop"). The source tree under `vendor/stargate/src/engine/` contains a pure C realtime audio engine; the GUI (`sgui/`) is written in Python with a custom framework (`sglib/`).

```
src/engine/
  include/audiodsp/          ← all DSP headers (ANSI C, no dependencies)
    lib/                     ← fundamental utilities (amp, pitch, interpolation, math …)
    modules/
      delay/                 ← chorus, delay, multi-comb, reverb
      distortion/            ← clipper, foldback, lofi, ring mod, saturator, soft-clipper …
      dynamics/              ← compressor, limiter, sidechain compressor
      filter/                ← SVF (state-variable), ladder, comb, peak-EQ, vocoder …
      modulation/            ← ADSR, envelope follower, ramp envelope, gate
      multifx/               ← multifx3knob / multifx10knob poly-modulation routers
      oscillator/            ← lfo_simple, noise, osc_simple (unison), osc_wavetable
      signal_routing/        ← amp_and_panner, audio_xfade, dry_wet, mixer_channel
  include/plugins/           ← per-plugin headers (va1, fm1, sampler1, reverb, eq …)
  src/audiodsp/              ← .c implementations of the above
  src/plugins/               ← .c implementations of the plugins
```

All floating point types are aliased as `SGFLT` (typically `float`). Allocations use `hpalloc()` (huge-page-aligned `mmap` on Linux, `malloc` elsewhere) from `lmalloc.h`.

---

### 1. Oscillator Core (`lib/osc_core.h`, `modules/oscillator/osc_simple.h`)

**`t_osc_core`** — minimal phasor:
```c
typedef struct {
    SGFLT output;   // [0, 1) — normalized phase
} t_osc_core;

void v_run_osc(t_osc_core *core, SGFLT inc);        // output += inc; if >= 1 → output -= 1
int  v_run_osc_sync(t_osc_core *core, SGFLT inc);   // returns 1 when phase wraps (hard sync trigger)
```

**`t_osc_simple_unison`** — full unison oscillator with up to `OSC_UNISON_MAX_VOICES = 7` voices:

```c
typedef struct {
    int voice_count;
    fp_get_osc_func_ptr osc_type;       // function pointer: f_get_saw / sine / square / triangle / off
    SGFLT voice_inc[OSC_UNISON_MAX_VOICES];
    t_osc_core osc_cores[OSC_UNISON_MAX_VOICES];
    SGFLT phases[OSC_UNISON_MAX_VOICES]; // per-voice phase offsets (spread)
    SGFLT uni_spread;
    SGFLT adjusted_amp;                  // auto-scaled to avoid volume increase with more voices
    SGFLT current_sample;
    int is_resetting;                    // used for hard sync
} t_osc_simple_unison;
```

Wave shapes are bare function pointers:
```c
SGFLT f_get_saw(t_osc_core*);       // -1 + phase*2
SGFLT f_get_sine(t_osc_core*);      // fast-sine table lookup
SGFLT f_get_square(t_osc_core*);    // phase > 0.5 ? 1 : -1
SGFLT f_get_triangle(t_osc_core*);  // |phase - 0.5| * 4 - 1 piecewise
SGFLT f_get_osc_off(t_osc_core*);   // 0
```

`v_osc_set_unison_pitch(osc, spread, pitch)` distributes the detuning across voices; `v_osc_note_on_sync_phases()` resets all voice phases to their stored initial values (phase-coherent note start); `f_osc_run_unison_osc_sync()` supports hard oscillator sync via the zero-crossing signal from `v_run_osc_sync`.

**`fast_sine.h`** — sine approximation via a 4096-entry table with linear interpolation, used via:
```c
f_sine_fast_run(&fast_sine_state, phase_0_to_1)
```

---

### 2. Pitch Core (`lib/pitch_core.h`)

MIDI note ↔ Hz conversions with fast and exact variants:

```c
SGFLT f_pit_midi_note_to_hz(SGFLT note);             // exact: 440 * pow(2, (note-69)/12)
SGFLT f_pit_midi_note_to_hz_fast(SGFLT note);        // 2521-entry table lookup + linear interp
SGFLT f_pit_hz_to_midi_note(SGFLT hz);               // inverse: 69 + 12*log2(hz/440)
SGFLT f_pit_midi_note_to_samples(SGFLT note, SGFLT sr); // wavelength in samples at that pitch
SGFLT f_pit_midi_note_to_ratio_fast(SGFLT base, SGFLT transposed, t_pit_ratio*);
```

The fast table covers MIDI range 20–124 (2521 entries including fractional headroom).  
`t_pit_ratio` caches `{ pitch, hz, hz_recip }` to avoid redundant computations in tight voice loops.

---

### 3. Amplitude & Math (`lib/amp.h`, `lib/math.h`)

```c
SGFLT f_db_to_linear(SGFLT db);           // pow(10, db/20)
SGFLT f_db_to_linear_fast(SGFLT db);      // table-accelerated version
SGFLT f_linear_to_db(SGFLT linear);       // 20*log10(linear)
```

`lib/math.h` adds:
```c
SGFLT f_sg_pow2(SGFLT x);       // 2^x approximation via integer bit-trick
SGFLT f_clip_value(SGFLT, SGFLT min, SGFLT max);
```

`lib/denormal.h` provides `f_remove_denormal(x)` — zeroes subnormal floats to avoid CPU stalls.

---

### 4. Interpolation (`lib/interpolate-linear.h`, `interpolate-cubic.h`, `interpolate-sinc.h`)

```c
// Linear
SGFLT f_linear_interpolate(SGFLT a, SGFLT b, SGFLT pos);  // a + (b-a)*pos

// Cubic (4-point Catmull-Rom)
SGFLT f_cubic_interpolate(SGFLT a, SGFLT b, SGFLT c, SGFLT d, SGFLT pos);

// Sinc (windowed sinc, used for high-quality sample playback)
SGFLT f_sinc_interpolate(SGFLT* buf, SGFLT pos, int size);
```

`lib/resampler_linear.h` provides a streaming linear-interpolation resampler for pitch-shifted sample playback in instruments.

---

### 5. State Variable Filter (`modules/filter/svf.h`)

The SVF is the primary filter throughout Stargate — used in reverb diffusers, the VA1 synth filter, the compressor side-chain, and the limiter's lookahead smoothing.

```c
typedef struct {
    SGFLT cutoff_note, cutoff_hz, cutoff_filter, pi2_div_sr;
    SGFLT filter_res, filter_res_db;
    SGFLT cutoff_base, cutoff_mod;
    SGFLT gain_db, gain_linear;          // for EQ type
    t_svf_kernel filter_kernels[SVF_MAX_CASCADE]; // SVF_MAX_CASCADE = 2 → max 4-pole
} t_state_variable_filter;
```

**`t_svf_kernel`** — one 2-pole SVF stage (Chamberlin topology):
```c
typedef struct {
    SGFLT filter_input, filter_last_input;
    SGFLT bp, bp_m1, lp, lp_m1, hp;
} t_svf_kernel;
```

**Core update** (4× oversampled, `SVF_OVERSAMPLE_MULTIPLIER = 4`):
```c
// v_svf_set_input_value steps through 4 sub-samples via linear interpolation
// from filter_last_input to filter_input, running each sub-iteration:
hp = input - lp_m1 - res * bp_m1;
bp = f * hp + bp_m1;
lp = f * bp + lp_m1;
// where f = pi2_div_sr * cutoff_hz (pre-computed coefficient)
```

Available function pointers (selected via `svf_get_run_filter_ptr(cascades, type)`):

| Function | Response |
|----------|---------|
| `v_svf_run_2_pole_lp` / `4_pole_lp` | 12/24 dB/oct lowpass |
| `v_svf_run_2_pole_hp` / `4_pole_hp` | 12/24 dB/oct highpass |
| `v_svf_run_2_pole_bp` / `4_pole_bp` | 6/12 dB/oct bandpass |
| `v_svf_run_2_pole_notch` / `4_pole_notch` | Notch |
| `v_svf_run_2_pole_eq` / `4_pole_eq` | Peaking EQ (gain_linear applied to BP output) |
| `v_svf_run_2_pole_allpass` | Allpass (used in reverb diffusers) |
| `v_svf_run_no_filter` | Bypass (no processing) |

Cutoff is set in MIDI note numbers via `v_svf_set_cutoff_base(svf, note)` + `v_svf_set_cutoff(svf)` which calls `f_pit_midi_note_to_hz_fast()` and recomputes `f = 2π × hz / sr`.

---

### 6. Other Filter Types

**`filter/ladder.h`** — Moog ladder filter (used in VA1):  
4-pole, with feedback coefficient and tanh nonlinearity for self-oscillation character.

**`filter/nosvf.h`** — "No-SVF" simpler filter:  
Used as an anti-aliasing filter in VA1's mono modules (post-processing path).

**`filter/comb_filter.h`** — Feedback comb filter (used in reverb taps):  
Circular buffer + feedback gain; delay time set in MIDI pitch note for tuned combs.

**`filter/peak_eq.h`** — RBJ biquad peaking EQ.  
**`filter/vocoder.h`** — Filterbank vocoder (N bands of band-pass filters tracking carrier vs. modulator).  
**`filter/formant_filter.h`** — Formant vowel filter (parallel SVF bank tuned to F1/F2/F3).

---

### 7. ADSR Envelope (`modules/modulation/adsr.h`)

Full DAHDSR with dual modes (linear and dB-domain):

```c
// Stages: DELAY(0) → ATTACK(1) → HOLD(2) → DECAY(3) → SUSTAIN(4) → RELEASE(5) → WAIT(6) → OFF(7)
typedef struct st_adsr {
    SGFLT output, output_db;
    int stage;
    SGFLT a_inc, d_inc, s_value, r_inc;       // linear increments per sample
    SGFLT a_inc_db, d_inc_db, r_inc_db;        // dB-domain increments
    SGFLT a_time, d_time, r_time;
    int time_counter, delay_count, hold_count, wait_count;
} t_adsr;
```

Two run modes selected via function pointer arrays:
- `v_adsr_run(t_adsr*)` — linear domain (used for amplitude envelopes with linear response)
- `v_adsr_run_db(t_adsr*)` — logarithmic domain (uses `ADSR_DB = 18 dB` range for attack/decay, `ADSR_DB_RELEASE = 48 dB` for release)

Release slope terminates at `ADSR_DB_THRESHOLD_LINEAR_RELEASE = 0.00390625` (= 2^-8 ≈ -48 dBFS).

Additional envelope types:
- **`ramp_env.h`** — simple linear ramp envelope (glide / pitch bend)
- **`perc_env.h`** — percussive exponential decay (used in FM1 for fast transient control)
- **`env_follower.h`** / **`env_follower2.h`** — RMS/peak envelope follower for dynamics detection
- **`gate.h`** — noise gate with threshold/hold/release

---

### 8. Compressor (`modules/dynamics/compressor.h`)

```c
typedef struct {
    SGFLT thresh, ratio, ratio_recip, knee, knee_thresh;
    SGFLT gain, gain_lin;
    t_state_variable_filter filter;    // LP side-chain filter
    SGFLT output0, output1;
    SGFLT rms_time, rms_last, rms_sum;
    int rms_counter, rms_count;
    t_enf2_env_follower env_follower;  // peak/RMS tracking
    t_pkm_redux peak_tracker;
} t_cmp_compressor;
```

Two run modes:
- `v_cmp_run(cmp, in0, in1)` — peak-detection compressor
- `v_cmp_run_rms(cmp, in0, in1)` — RMS-detection compressor (time-windowed RMS sum)

Gain computation: soft-knee region blends between 1:1 and `1/ratio` gain reduction around `thresh ± knee/2`. An optional LP side-chain filter (`t_state_variable_filter`) pre-filters the detection signal for frequency-selective compression.

---

### 9. Limiter (`modules/dynamics/limiter.h`)

Look-ahead brick-wall limiter:

```c
typedef struct st_lim_limiter {
    SGFLT thresh, ceiling, volume, release;
    SGFLT maxSpls, max1Block, max2Block;   // dual-block peak holding
    SGFLT envT, env, gain;
    int holdtime, r1Timer, r2Timer;        // hold + release timers
    SGFLT *buffer0, *buffer1;              // look-ahead delay buffers
    int buffer_size, buffer_index, buffer_read_index;
    t_state_variable_filter filter;        // smoothing LP
    t_pkm_redux peak_tracker;
} t_lim_limiter;
```

Hold time: `holdtime = sr / SG_HOLD_TIME_DIVISOR` (500 ms divisor).  
Two-block peak hold: `max1Block` tracks the current period's peak, `max2Block` holds the previous. Release is applied only after both blocks drop below threshold.  
Look-ahead buffer size allows the gain reduction to be applied `buffer_size` samples before the detected peak, guaranteeing no overshoot above `ceiling`.

---

### 10. Reverb (`modules/delay/reverb.h`)

```c
#define REVERB_DIFFUSER_COUNT 5
#define REVERB_TAP_COUNT 12

typedef struct {
    SGFLT output[2];
    SGFLT feedback;
    t_lfs_lfo lfo;                      // LFO modulates diffuser allpass frequencies
    t_state_variable_filter lp, hp;     // color (LP) and rumble cut (HP)
    t_rvb_tap taps[12];                 // feedback comb filters
    t_rvb_diffuser diffusers[5];        // SVF allpass diffusers
    SGFLT *predelay_buffer[2];          // stereo predelay circular buffer
    int predelay_counter, predelay_size;
} t_rvb_reverb;
```

**Signal path:**
1. Sum stereo input → LP (color control) → HP (hp_cutoff)
2. Scale by `wet_linear`
3. Feed through 12 parallel comb filters (tuned to MIDI-note pitches from `30 - time*25` stepping by `1.4 + time*0.8`) with feedback = `time - 1.03`
4. Sum comb outputs into stereo output (accumulated, not mixed — gives dense early reflections)
5. Each output channel passes through 5 serial allpass SVF diffusers; L and R use opposing LFO offsets (`±lfo.output * 2.0`) on each diffuser's cutoff — creates stereo width and decorrelation
6. Write/read stereo predelay ring buffer (up to ~1 s at 44100 Hz + 5000-sample headroom)

`v_rvb_panic()` zeros all comb and predelay buffers (used on MIDI panic / stop).

---

### 11. Chorus & Delay (`modules/delay/`)

**`chorus.h`** — stereo chorus:  
Two SVF allpass-modulated delay lines with an LFO (`t_lfs_lfo`) for sweep, depth controls rate and depth of modulation.

**`delay.h`** / **`delay_plugin.h`** — feedback delay:  
Circular buffer with tempo-sync time, feedback, ping-pong mode, and wet/dry.

**`multi_comb_filter.h`** — parallel comb filter bank:  
Used for more complex resonant delay effects (e.g., metallic/spring reverb character).

---

### 12. Distortion (`modules/distortion/`)

| Module | Algorithm |
|--------|-----------|
| `clipper.h` | Hard clip to ±ceiling |
| `soft_clipper.h` | Polynomial soft clip: `x / (1 + |x|^n)^(1/n)` |
| `saturator.h` | Waveshaper with adjustable drive + bias |
| `foldback.h` | Wavefolding: reflects signal back when it exceeds threshold |
| `ring_mod.h` | Ring modulation: `out = in * osc_output` |
| `lofi.h` | Bit-depth + sample-rate reduction |
| `glitch.h` / `glitch_v2.h` | Buffer stutter/repeat effect |
| `poly_glitch.h` | Per-voice polyphonic stutter |
| `sample_and_hold.h` | Sample-and-hold quantization with independent rate |
| `multi.h` | Distortion router: selects between multiple waveshaper types via function pointer |

---

### 13. LFO (`modules/oscillator/lfo_simple.h`)

```c
typedef struct {
    SGFLT output;
    SGFLT inc;
    SGFLT phase;
} t_lfs_lfo;

void v_lfs_set(t_lfs_lfo*, SGFLT freq_hz);
void v_lfs_run(t_lfs_lfo*);  // phase += inc; if >= 1 → -= 1; output = sin(2π*phase)
```

Used pervasively: oscillator vibrato, reverb diffuser modulation, chorus sweep.  
The sine value is obtained from the same `fast_sine` table as the oscillator.

---

### 14. Instrument Plugins

#### VA1 — Virtual Analog Synthesizer

Full-featured subtractive synth with 24-voice polyphony:
- **2 oscillators** (`t_osc_simple_unison`), each with up to 7 unison voices, types: sine/saw/square/triangle/noise + off
- **Hard sync**: osc2 resets osc1 on zero-crossing via `v_run_osc_sync`
- **Noise generator**: white/pink selectable  
- **Filter**: selectable between Moog ladder (`ladder.h`) and SVF (`svf.h`) with ADSR filter envelope and key-tracking
- **Amplitude ADSR** (linear or dB mode)
- **LFO** → modulates amplitude, pitch (coarse + fine), filter cutoff
- **Pitch envelope** (ramp) + glide (portamento) smoother
- **Multi-distortion** (`multi.h`) with wet control
- **AA filter** for output (`nosvf.h`)
- **Per-note panning** + per-instrument pan control

Key params exposed: 65 control ports (`VA1_COUNT = 65`) covering every synth parameter. Per-voice modulation by MIDI velocity across `ATTACK_PMN_START/END`, `DECAY_PMN_START/END`, etc. (velocity-to-parameter mapping).

#### FM1 — FM Synthesizer / Sample-based (wavetable)

Complex multi-algorithm FM synth:
- **6 oscillators** (`FM1_OSC_COUNT = 6`), each can be a wavetable shape or FM operator
- **FM macro controls** × 2: macro knobs sweep multiple operator ratios simultaneously
- **4 ADSRs** + LFO + percussion envelope (`perc_env`)
- **4 PolyFX slots** (`multifx3knob`) with a modulation matrix of 8 sources × 4 destinations
- **SVF filter**, noise generator, clipper distortion, resampler (`resampler_linear`)
- `FM1_MODULATOR_COUNT = 8` sources: envelope × 4, LFO, velocity, pitch, key  
- `FM1_MODULAR_POLYFX_COUNT = 4` slots each with 3 knobs + type selector

#### Sampler1

SFZ-compatible sample player: loads SFZ instrument maps from `sglib/`-packaged instruments. Supports per-note sample zones, looping, ADSR, LFO, filter, tuning.

---

### 15. Effect Plugins (`include/plugins/`)

| Plugin | Core algorithm |
|--------|---------------|
| `reverb.h` | `t_rvb_reverb` — 12 tap + 5 allpass diffuser (see §10) |
| `delay.h` | Stereo feedback delay with tempo-sync |
| `eq.h` | Multiband parametric EQ using `peak_eq.h` biquad sections |
| `compressor.h` | Peak + RMS compressor (see §8) |
| `limiter.h` | Look-ahead limiter (see §9) |
| `sidechain_comp.h` | Compressor with external sidechain input |
| `multifx.h` | Per-track multi-effect with routing matrix |
| `nabu.h` | Stereo widener / mid-side processor |
| `pitchglitch.h` | Pitch glitch / stutter buffer effect |
| `vocoder.h` | Filterbank vocoder (`vocoder.h` SVF bank) |
| `widemixer.h` | Parallel mid/side mixing with width control |
| `xfade.h` | Crossfader between two audio paths |
| `simple_fader.h` | Gain + pan fader |
| `trigger_fx.h` | MIDI-trigger-controlled effect gate |

---

### 16. Signal Routing

**`signal_routing/mixer_channel.h`** — per-channel mixer strip:  
Gain, pan (`t_pn2_panner2`), send levels to aux buses, effect chain.

**`signal_routing/audio_xfade.h`** — equal-power crossfade (`SGFLT` × 2):
```c
out0 = in0 * cos(x * π/2);   out1 = in1 * sin(x * π/2);
```

**`signal_routing/dry_wet.h`** / **`dry_wet_pan.h`** — wet/dry blend + optional post-pan.

**`signal_routing/panner2.h`** — stereo panner:  
`t_pn2_panner2` stores computed L/R gain pair from a pan value in [-1, 1], updated lazily only when pan value changes.

---

### 17. Smoother Modules

**`lib/smoother-linear.h`** — sample-accurate linear smoother:  
Interpolates between old and new value over a fixed number of samples (`t_smoother_linear`). Used in VA1 for filter cutoff, pitchbend, LFO depth to prevent zipper noise.

**`lib/smoother-iir.h`** — single-pole IIR smoother:  
`out = coeff * out + (1.0 - coeff) * target`. Faster than linear; used for less critical parameters.

---

### 18. Integration Notes for `rhythm-vibe-mcp`

| Use-case | Relevant stargate code |
|----------|----------------------|
| **State-variable filter** | `audiodsp/modules/filter/svf.h` + `svf.c` — pure C, no deps; exposes LP/HP/BP/notch/EQ/allpass via function pointer; extractable as-is |
| **Reverb** | `modules/delay/reverb.h/c` — 12 comb + 5 allpass diffuser, stereo, predelay; only deps are `lmalloc`, `pitch_core`, `comb_filter`, `svf`, `lfo_simple` — all pure C |
| **Compressor / Limiter** | `dynamics/compressor.h/c`, `dynamics/limiter.h/c` — lookahead limiter and peak/RMS compressor; pure C |
| **ADSR envelope** | `modulation/adsr.h/c` — 7-stage DAHDSR with linear + dB modes; no external deps |
| **Oscillator unison** | `oscillator/osc_simple.h` — 7-voice unison with pitching, type function pointer, sync; pure C |
| **Pitch utilities** | `lib/pitch_core.h` — MIDI↔Hz with fast table; `lib/amp.h` — dB↔linear; all pure C header/src pairs |
| **Interpolation** | `lib/interpolate-linear/cubic/sinc.h` — 3 quality levels; suitable for pitched sample read-back |
| **Distortion menu** | `audiodsp/modules/distortion/` — 10 independent single-header waveshapers, selectable via `multi.h` function pointer router |
| **Vocoder / Formant** | `filter/vocoder.h`, `filter/formant_filter.h` — SVF-bank vocal effects; directly portable |

---

## tenacity

> **Repository origin:** `vendor/tenacity/`  
> **Language:** C++ (C++17), wxWidgets UI  
> **License:** GPL v2 or later  
> **Role in rhythm-vibe-mcp:** A deeply researched reference for production-quality audio DSP algorithms: spectral noise reduction, Freeverb-topology reverb, lookahead compressor/limiter, phaser/wah-wah allpass chains, distortion waveshaping, FFT-based convolution EQ, multi-algorithm time-stretching/pitch-shifting, and a full MIR (tempo detection) library — all implemented in approachable, well-documented C++.

### Overview

Tenacity is a fork of Audacity — a multi-track audio editor and recorder — created in response to Audacity's telemetry and CLA controversies. It is feature-compatible with Audacity 3.x while the team adds its own improvements (Matroska I/O, Haiku support, modern build system, revamped themes). It ships a complete DSP stack structured as ~50 independently compilable `libraries/lib-*` modules under a CMake build.

```
vendor/tenacity/
  src/                           ← top-level app / UI (wxWidgets, commands, menus)
  src/effects/                   ← thin UI wrappers over library effect "Base" classes
  libraries/
    lib-builtin-effects/         ← algorithmic effect implementations
    lib-dynamic-range-processor/ ← compressor + limiter (Daniel Rudrich algorithm)
    lib-fft/                     ← FFT, power spectrum, windowing
    lib-math/                    ← Reverb_libSoX, Resample (soxr), Biquad
    lib-time-and-pitch/          ← StaffPad time-stretch, FormantShifter
    lib-music-information-retrieval/ ← beat/tempo detection (onset + autocorr)
    lib-wave-track-fft/          ← TrackSpectrumTransformer (STFT helper)
    lib-audio-io/                ← PortAudio / PortMidi realtime I/O
    lib-stretching-sequence/     ← clip-level time-stretching pipeline
    lib-lv2 / lib-vst / lib-vst3 / lib-audio-unit ← plugin hosting
  lib-src/
    libnyquist/                  ← embedded Nyquist/SAL scripting language (DSP)
    pffft/                       ← SIMD-accelerated split-radix FFT backend
  nyquist/                       ← built-in Nyquist plug-ins (filters, analysis …)
  plug-ins/                      ← shipped LADSPA/Nyquist effect plug-ins
```

---

### 1. FFT Infrastructure (`libraries/lib-fft/`)

**`FFT.h`** — high-level convenience API:

```cpp
// All sizes must be a power of two; single-precision floats throughout
void PowerSpectrum(size_t N, const float* in, float* out);      // sum(re²+im²)/N, output is N/2 long
void RealFFT(size_t N, const float* re_in, float* re_out, float* im_out);
void InverseRealFFT(size_t N, const float* re, const float* im, float* re_out);
void FFT(size_t N, bool inverse, const float* reIn, const float* imIn, float* reOut, float* imOut);
```

Window functions (`eWindowFunctions`):

| Enum | Window |
|------|--------|
| `eWinFuncRectangular` | No window (rectangular) |
| `eWinFuncBartlett` | Bartlett (triangular) |
| `eWinFuncHamming` | Hamming |
| `eWinFuncHann` | Hann (von Hann) |
| `eWinFuncBlackman` | Blackman |
| `eWinFuncBlackmanHarris` | Blackman-Harris (4-term) |
| `eWinFuncWelch` | Welch (parabolic) |
| `eWinFuncGaussian25/35/45` | Gaussian with σ = 1/2.5, 1/3.5, 1/4.5 |

Two window application functions: `WindowFunc` (legacy, slightly asymmetric) and the corrected `NewWindowFunc` (symmetric about `N/2`). A `DerivativeOfWindowFunc` is also provided for STFT reassignment applications.

**`RealFFTf.h`** — split-radix real FFT with precomputed tables:

```cpp
struct FFTParam {
    ArrayOf<int>      BitReversed;   // bit-reversal permutation
    ArrayOf<fft_type> SinTable;      // combined sin/cos twiddle table
    size_t            Points;
};
HFFT GetFFT(size_t size);                                    // cached factory
void RealFFTf(fft_type*, const FFTParam*);                   // in-place forward
void InverseRealFFTf(fft_type*, const FFTParam*);             // in-place inverse
void ReorderToTime(const FFTParam*, const fft_type*, fft_type*);
void ReorderToFreq(const FFTParam*, const fft_type*, float* re, float* im);
```

**`lib-src/pffft/`** — PFFFT (Pretty Fast FFT): SIMD-vectorized (SSE/NEON) split-radix FFT used as an optional accelerated back-end.

---

### 2. Resampling (`libraries/lib-math/Resample.h`)

Wraps **libsoxr** (SoX Resampler Library), the standard in high-quality sample-rate conversion:

```cpp
class Resample {
    // Two quality presets selectable per-session:
    static EnumSetting<int> FastMethodSetting;   // for real-time I/O
    static EnumSetting<int> BestMethodSetting;   // for offline mixing/export

    // streaming resampler — variable rate supported
    std::pair<size_t,size_t> Process(double factor,
                                     const float* inBuf, size_t inLen, bool last,
                                     float* outBuf, size_t outLen);
};
```

Supports constant-rate and variable-rate (for time warpers). The "Best" preset uses a Kaiser-windowed sinc of length selected to meet a ≥ 100 dB stopband attenuation target.

---

### 3. Reverb (`libraries/lib-math/Reverb_libSoX.h`)

**Algorithm**: Freeverb topology ported from libSoX (robs@users.sourceforge.net, LGPL v2.1).

**Signal graph** per channel:
1. HP pre-filter → LP pre-filter (one-pole IIR, `one_pole_t`)
2. 8 parallel **feedback comb filters** (Schroeder combs):
   - Delay lengths at 44100 Hz: `{1116, 1188, 1277, 1356, 1422, 1491, 1557, 1617}` samples
   - Scaled for actual sample rate: `size = (int)(scale × rate/44100 × (base_len + stereo_adjust × offset) + 0.5)`
   - Each comb applies HF damping: `store = output + (store - output) × hf_damping`; feedback = `store × feedback_coeff`
3. 4 serial **allpass diffusers**: `{225, 341, 441, 556}` samples; fixed feedback = 0.5
4. Stereo decorrelation: right channel lengths shifted by `stereo_adjust = 12` samples

```c
// Comb filter core (inlined by gcc -O2):
float comb_process(filter_t* p, float* input, float* feedback, float* hf_damping) {
    float output = *p->ptr;
    p->store = output + (p->store - output) * *hf_damping;
    *p->ptr = *input + p->store * *feedback;
    filter_advance(p);
    return output;
}

// Allpass diffuser core:
float allpass_process(filter_t* p, float* input) {
    float output = *p->ptr;
    *p->ptr = *input + output * 0.5f;
    filter_advance(p);
    return output - *input;
}
```

**Parameters**: `RoomSize` (0–100) → comb delay scale factor; `Reverberance` (0–100) → feedback coefficient; `HfDamping` (0–100); `ToneLow/High` (HP/LP cutoff levels); `PreDelay` (0–200 ms via `fifo_t` buffer); `StereoWidth` (0–100) → L/R blend of dual filter banks; `WetGain` / `DryGain` dB; `WetOnly` toggle.

---

### 4. Phaser (`libraries/lib-builtin-effects/PhaserBase.h`)

LFO-driven allpass phaser with up to 24 stages:

```cpp
class EffectPhaserState {
    double old[NUM_STAGES]; // NUM_STAGES = 24 allpass state variables
    double gain, fbout, outgain;
    double lfoskip;         // LFO phase increment per sample
    double phase;           // LFO running phase
    int laststages;
};
```

**Signal path** (per sample):
1. Compute LFO: `lfoout = depth * sin(2π × phase)` where `phase += lfoskip`
2. Feed through N second-order allpass stages (Schroeder allpass lattice form):  `filtered = lfoout * in + gain × old[i] - in; old[i] = filtered` (with `Coefficients()` computing RBJ allpass biquad coefficients at each LFO modulation tick)
3. Mix dry/wet: `out = (in + feedback × fbout + (dryWet/255) × filtered) × outgain`

**Parameters**: `Stages` (2–24, even recommended); `Freq` (0.001–4 Hz); `Phase` (0–360°, for stereo);  `Depth` (0–255); `Feedback` (−100–+100%); `DryWet` (0–255); `OutGain` (−30–+30 dB).

Supports full realtime operation (RealtimeSince::Always).

---

### 5. Wah-Wah (`libraries/lib-builtin-effects/WahWahBase.h`)

LFO-modulated biquad bandpass filter:

```cpp
class EffectWahwahState {
    double xn1, xn2, yn1, yn2;          // biquad delay line
    double b0, b1, b2, a0, a1, a2;      // biquad coefficients (recomputed per LFO step)
    double phase;                         // LFO phase
    double lfoskip;                       // LFO increment
    double freqofs;                       // center frequency offset ratio [0,1]
    double depth;                         // sweep depth [0,1]
};
```

**Algorithm** (per sample):
1. Compute LFO: `lfoout = depth × (1 + sin(2π × phase / 2π))` → maps LFO to [0, depth]
2. Compute swept center frequency: `frequency = (FreqOffset + lfoout) × (samplerate / 2) / 100.0`
3. Compute RBJ bandpass biquad coefficients with resonance Q = `mRes`
4. Apply direct-form II biquad: `out = b0×in + b1×xn1 + b2×xn2 - a1×yn1 - a2×yn2`

**Parameters**: `Freq` (0.1–4 Hz LFO); `Phase` (0–360° for stereo offset); `Depth` (0–100%); `Resonance` (0.1–10.0); `FreqOffset` (0–100%); `OutGain` (−30–+30 dB).

---

### 6. Distortion (`libraries/lib-builtin-effects/DistortionBase.h`)

Lookup-table waveshaper with 11 table types and an optional DC-block filter:

```cpp
#define TABLESIZE 2049  // maps input [-1, 1] through 2048 steps to output

enum kTableType {
    kHardClip,
    kSoftClip,         // log-curve: y = T + (e^(R*T − R*x) − 1) / −R
    kHalfSinCurve,
    kExpCurve,         // exponential mapping
    kLogCurve,         // logarithmic mapping
    kCubic,            // y = x − x³/3 (Chebyshev T₃/3)
    kEvenHarmonics,    // even-order harmonic content
    kSinCurve,
    kLeveller,         // modeled on legacy "Leveller" effect (multi-stage gain)
    kRectifier,        // 0%=dry → 50%=half-wave rect → 100%=full-wave |x|
    kHardLimiter,      // replicates LADSPA "hardLimiter 1413"
    nTableTypes
};
```

Tables are pre-built once from `threshold_dB`, `param1`, `param2`, then applied per-sample as a lookup + linear interpolation between adjacent table entries. Symmetric tables use `CopyHalfTable()`. A DC-block filter (queue-based running-average subtract) can be inserted post-waveshaping.  
`mRepeats` applies the full waveshaper chain multiple times for heavier saturation. Unity gain is restored via `mMakeupGain`.

---

### 7. Bass and Treble (`libraries/lib-builtin-effects/BassTrebleBase.h`)

Two independent second-order RBJ shelving biquad filters:

```cpp
class BassTrebleState {
    // Bass shelf biquad (low-shelf at hzBass Hz):
    double a0Bass, a1Bass, a2Bass, b0Bass, b1Bass, b2Bass;
    double xn1Bass, xn2Bass, yn1Bass, yn2Bass;
    // Treble shelf biquad (high-shelf at hzTreble Hz):
    double a0Treble, a1Treble, a2Treble, b0Treble, b1Treble, b2Treble;
    double xn1Treble, xn2Treble, yn1Treble, yn2Treble;
};
```

Coefficients are computed via `Coefficients(hz, slope, gain, samplerate, type, …)` using the RBJ cookbook formulas for shelving EQ. Bass ±30 dB at 250 Hz (low-shelf); treble ±30 dB at 4000 Hz (high-shelf). Realtime capable. `Link` slider syncs bass and treble for coupled adjustment.

---

### 8. Scientific Filter (`libraries/lib-builtin-effects/ScienFilterBase.h` + `lib-math/Biquad.h`)

Cascaded biquad IIR filter with filter type and approximation choices:

- **Filter types**: Lowpass, Highpass, Bandpass, Bandstop (notch)
- **Approximations**: Butterworth, Chebyshev Type I, Chebyshev Type II, Elliptic (Cauer)
- **Order**: 1–10 (configurable, generates N/2 second-order sections)

Coefficients are computed analytically using the appropriate polynomial design (Butterworth: maximally flat; Chebyshev I: equiripple passband; Chebyshev II: equiripple stopband; Elliptic: equiripple both bands). Each section is a direct-form II biquad from `Biquad.h`.

`FilterMagnAtFreq(float hz)` evaluates the filter's transfer function magnitude for the plot display.

---

### 9. FFT-based Convolution EQ (`libraries/lib-builtin-effects/EqualizationBase.h`)

Linear-phase FIR equalizer designed by drawing a frequency-response curve:

1. User draws a response curve in the EQ panel (or selects a factory preset)
2. Inverse FFT of the drawn response → time-domain FIR kernel (window-sinc design)
3. **Overlap-add** convolution: input is blocked into windows; each block is multiplied in the frequency domain with the pre-transformed FIR spectrum; time-domain frames are overlap-added with 50% overlap using a Hann window pair
4. Left-tail trimming (`leftTailRemaining = (M−1)/2`) removes the symmetric pre-ringing typical of linear-phase FIR filters

The EQ comes in two modes (`kEqLegacy` and a newer filter mode) and ships a library of factory preset curves (classical room EQs, telephone, AM radio, vocal presence, etc.).

---

### 10. Noise Reduction (`libraries/lib-builtin-effects/NoiseReductionBase.cpp`)

Two-pass spectral-envelope subtraction with time and frequency smoothing:

**Pass 1 — Profile collection:**
- For each overlapping window of the noise-only sample: compute FFT → per-bin amplitude statistics (`mSums`, `mMeans`)
- Statistics method: second-greatest amplitude across frames per bin (default), or median

**Pass 2 — Reduction:**
- For each windowed frame of the signal: FFT → compute per-bin gain:
  - If amplitude > `noise_threshold × sensitivity` → pass (0 dB gain)
  - Else → suppress by `−mNoiseGain dB` (default −18 dB)
- **Time smoothing**: gain for each bin moves at attack rate `mAttackTime` (rise) and release rate `mReleaseTime` (fall) — prevents chattering
- **Frequency smoothing**: per-bin gain is low-pass filtered across `mFreqSmoothingBands` neighboring bins — prevents isolated single-frequency suppression artifacts
- Apply complex gain to FFT bins → IFFT → overlap-add with matching synthesis window

Window pairs (analysis/synthesis):
- `Hann / Hann` (default, requires ≥ 4 steps per window)
- `Rectangular / Hann`, `Blackman / Hann`, `Hamming / Hann`, etc.

Modes: `NRC_REDUCE_NOISE` (subtract profile), `NRC_ISOLATE_NOISE` (pass only noise), `NRC_LEAVE_RESIDUE` (what was subtracted). Not realtime (offline only, uses lookahead).

---

### 11. Compressor & Limiter (`libraries/lib-dynamic-range-processor/`)

Modern lookahead compressor built on **Daniel Rudrich's** gain-reduction engine:

```cpp
// Key settings (from DynamicRangeProcessorTypes.h):
struct CompressorSettings {
    double thresholdDb  = -10;   // dB
    double makeupGainDb =   0;   // dB
    double kneeWidthDb  =   5;   // dB (soft knee)
    double compressionRatio = 10;
    double lookaheadMs  =   1;   // up to 1000 ms
    double attackMs     =  30;
    double releaseMs    = 150;
};
struct LimiterSettings {
    // compressionRatio → ∞ (infinity), attackMs → 0
    double thresholdDb      = -5;
    double makeupTargetDb   = -1;
    double kneeWidthDb      =  2;
    double lookaheadMs      =  1;   // up to 50 ms
    double releaseMs        = 20;
};
```

**Processing pipeline** (`CompressorProcessor`):
1. `UpdateEnvelope()` — `GainReductionComputer` evaluates the transfer function per sample: below knee → unity; in knee → smooth interpolation; above threshold → `1/ratio` gain reduction; result: envelope in dB
2. `CopyWithDelay()` — lookahead circular buffer copies input delayed by `lookaheadMs × sr` samples
3. `ApplyEnvelope()` — multiply delayed signal by `10^(envelope_dB/20)` → output

Transfer function:
$$
GR(x) = \begin{cases}
0 & x \le T - W/2 \\
\frac{(x - T + W/2)^2}{2W(1 - 1/R)} & T - W/2 < x \le T + W/2 \quad \text{(soft knee)} \\
(x - T) \cdot (1 - 1/R) & x > T + W/2
\end{cases}
$$

Where $T$ = threshold, $W$ = knee width, $R$ = ratio (∞ for limiter).

Metering runs on a lock-free queue at 30 fps; both target (computed) and actual (applied after lookahead) compression values are tracked for display.

---

### 12. Time-Stretching and Pitch-Shifting

Tenacity ships three independent algorithms:

#### 12a. StaffPad (High Quality, Realtime-capable)

`lib-time-and-pitch/StaffPadTimeAndPitch.h` wraps `staffpad::TimeAndPitch`:

```cpp
struct Parameters {
    double timeRatio     = 1.0;   // output_duration / input_duration
    double pitchRatio    = 1.0;   // pitch factor (2.0 = +1 octave)
    bool preserveFormants = false;
};
// Pitch range: MinCents = -1200 to MaxCents = +1200 (±1 octave)
```

The `FormantShifter` separates the spectral envelope (formants) from the excitation signal before pitch shifting, then re-applies the original formant envelope after — producing natural-sounding pitch shifts without the "chipmunk" effect.

#### 12b. SoundTouch (Offline: ChangeTempo, ChangePitch)

`SoundTouchBase` wraps the **SoundTouch** library by Olli Parviainen: WSOLA-based time-stretching (Waveform Similarity Overlap-Add); pitch shifting via independent transposition stage. Used by `ChangeTempo` (pitch-preserving tempo change) and `ChangePitch` (tempo-preserving pitch change). Supports NoteTrack transposition via MIDI semitone adjustment.

#### 12c. Paulstretch (Extreme Stretch)

`PaulstretchBase` implements Paul Stretch by Nasca Octavian Paul:

```
Parameters: mAmount (stretch factor ≥ 1, default 10×), mTime_resolution (0.001–∞ s, default 0.25 s)
Algorithm per window:
  1. Window input with Hann window
  2. RealFFT
  3. Randomize all bin phases (keep magnitudes) → spectral "freeze"
  4. IFFT → overlap-add output with step = input_step / mAmount
```

At high stretch factors, the randomized phases eliminate pitch-periodicity, producing the signature ambient drone texture. Buffer size is tuned to `mTime_resolution × sampleRate` rounded to a power of two.

#### 12d. SBSMS (TimeScale: pitch + tempo envelope)

`SBSMSBase` wraps the **SBSMS** (Subband Sinusoidal Modeling and Synthesis) library. Used by the `TimeScale` effect for simultaneously varying tempo and pitch with linear, log, or sinusoidal slide envelopes (`SlideType`). Both rate and pitch can glide non-uniformly across the selection and may be linked or independent.

---

### 13. AutoDuck (`src/effects/AutoDuck.h`)

Side-chain envelope follower for ducking: analyzes an envelope track → applies gain reduction to a target track where the sidechain exceeds a threshold. Parameters: duck amount (dB), inner/outer fade lengths, side-chain threshold, and maximum pause between duck events.

---

### 14. Click Removal (`ClickRemovalBase`)

Iterative click detection and repair:
- Frame through audio with short analysis window
- Within each window: compute sum of absolute differences between adjacent samples; threshold to locate "spikes"
- Repair detected click region by linear interpolation across the corrupted segment

---

### 15. Loudness Normalization (`LoudnessBase`)

EBU R128 / ReplayGain integrated loudness normalization:
- Compute integrated loudness (LUFS) using K-weighted filtering (pre-filter + RLB weighting curve)
- Target: −23 LUFS (broadcast) or user-specified LUFS/RMS
- Optional stereo independent normalization

---

### 16. Truncate Silence (`TruncSilenceBase`)

Detect and remove or shorten silent regions:
- RMS analysis over short (configurable) windows
- Silence threshold in dB; minimum silence duration before truncation
- Truncate modes: compress (shorten to a fixed duration) or remove entirely

---

### 17. Music Information Retrieval (`libraries/lib-music-information-retrieval/`)

Beat and tempo detection pipeline:

```
GetOnsetDetectionFunction() → onset strength per STFT frame
    ↓
GetNormalizedCircularAutocorr() → tempo period candidates
    ↓
GetMeterUsingTatumQuantizationFit() → best-fit BPM + tatum grid
    ↓
GetMusicalMeterFromSignal() → optional<MusicalMeter> with BPM + time signature
```

- **Onset detection**: spectral flux (L1 norm of positive spectral change) across STFT frames via `StftFrameProvider`
- **Autocorrelation**: normalized circular autocorrelation (power-of-2 input, output length N/2+1) — peaks at lag corresponding to beat period
- **Tatum quantization fit**: finds the integer tatum subdivision that best aligns onset times to a regular grid; two classifier thresholds (`FalsePositiveTolerance::Strict` ← 4% FPR / `Lenient` ← 10% FPR)
- **ACID tags**: reads `LibFileFormats::AcidizerTags` from WAV/AIFF for pre-embedded BPM metadata
- **`SynchronizeProject`**: auto-matches imported clips to project tempo using detected meter, optionally adjusting tempo or clip speed

`lib-wave-track-fft/TrackSpectrumTransformer` provides the sliding-window STFT buffer used by both MIR and the spectrogram display track.

---

### 18. Nyquist Scripting (`lib-src/libnyquist/`, `nyquist/`, `modules/nyquist/`)

Embedded Nyquist (Lisp-dialect) language for programmable DSP:
- Full signal-processing primitives: `(hzosc freq)`, `(lowpass8 sig hz)`, `(highpass8 sig hz)`, `(bandpass2 sig hz bw)`, `(reverb sig time)`, `(convolve sig ir)`, `(fft-filter sig response)`, `(sound-srate-abs sig sr)`, etc.
- Shipped built-in plug-ins include: noise gate, spectral analysis, adaptive filter, comb filter, cross-fade, click repair, pitch detect, etc.
- Nyquist plug-ins are plain `.ny` text files; new DSP algorithms can be prototyped in minutes without recompilation

---

### 19. Plugin Hosting

| Format | Library | Notes |
|--------|---------|-------|
| VST2 | `lib-vst/` | Scans and caches; offline and realtime capable |
| VST3 | `lib-vst3/` | Full VST3 bus layout; IEditController + IComponent |
| LV2 | `lib-lv2/` | Full feature set including worker threads and state save/restore |
| AudioUnit | `lib-audio-unit/` | macOS only; wraps AUv2 |
| LADSPA | `lib-ladspa/` | Simple C API; bundled with classic filter/EQ plug-ins |
| VAMP | `src/effects/VampEffect.h` | Feature extraction plug-ins (via libvamp) |

Realtime effects rack (`lib-realtime-effects/`): per-track non-destructive effect chains, updated per audio buffer, with lock-free parameter update from UI thread.

---

### 20. Audio I/O (`libraries/lib-audio-io/`)

PortAudio-based engine:
- Circular ring-buffer between disk read and playback threads
- Latency compensation for effect chains (reads `GetLatency()` from each effect)
- MIDI via PortMidi: note playback from NoteTrack, MIDI sync

---

### 21. Integration Notes for `rhythm-vibe-mcp`

| Use-case | Relevant Tenacity code |
|----------|----------------------|
| **Spectral noise reduction** | `NoiseReductionBase.cpp` — well-commented two-pass spectral subtraction; depends only on `lib-fft/FFT.h` and `TrackSpectrumTransformer`; extractable algorithm |
| **Freeverb reverb** | `Reverb_libSoX.h` — single self-contained header, LGPL; 8 combs + 4 allpass, stereo; parameterizable room size / reverberance / HF damping |
| **Lookahead compressor/limiter** | `lib-dynamic-range-processor/CompressorProcessor` — Daniel Rudrich algorithm; lookahead up to 1 s; real-time capable; includes metering via lock-free queue |
| **Distortion waveshaping** | `DistortionBase` — 11-type lookup table waveshaper with DC block; self-contained C++ |
| **Phaser** | `PhaserBase` — up to 24 allpass stages, realtime; stereo via phase offset |
| **Wah-wah** | `WahWahBase` — LFO biquad bandpass; minimal state (10 doubles) |
| **Shelving EQ** | `BassTrebleBase` — dual RBJ shelving biquad, realtime; ±30 dB |
| **Scientific filter** | `ScienFilterBase` + `Biquad.h` — up to 10th-order Butterworth/Chebyshev/Elliptic |
| **Convolution EQ** | `EqualizationBase` — overlap-add FFT EQ; linear phase; factory curve library |
| **Time-stretch / pitch** | `StaffPadTimeAndPitch` (best quality + formant preserve) or `SoundTouchBase` (WSOLA, faster) or `PaulstretchBase` (extreme ambient stretch) |
| **Tempo / beat detection** | `lib-music-information-retrieval` — onset → autocorr → tatum-fit; returns BPM + meter |
| **Resampling** | `Resample.h` → libsoxr; constant or variable rate; "fast" or "best" quality mode |
| **FFT / windowing** | `lib-fft/FFT.h` + `RealFFTf.h` — 9 window types; power spectrum, real FFT; pffft SIMD back-end available |

## tracktion_engine

> **Repository origin:** `vendor/tracktion_engine/`  
> **Language:** C++20, JUCE module  
> **License:** GPL v3 / commercial dual-license  
> **Role in rhythm-vibe-mcp:** A complete, high-level DAW data model and realtime audio graph — the foundation of Tracktion Waveform. Its `tracktion_graph` multi-CPU engine, built-in synthesis/effects plugin suite (4OSC, sampler, EQ, compressor, reverb, pitch-shifter…), MIDI pattern generation (arp/chord/bass/melody), clip-launching, and per-parameter modulation system make it the most comprehensive compositing engine in the vendor tree.

### Important Note

The engine source (`modules/tracktion_engine/`) is **not present** in this vendor copy — only the `modules/3rd_party/` dependencies were checked out. The engine itself is a submodule referencing the upstream repository. Documentation below is derived from `FEATURES.md`, demo sources, and the 3rd-party headers that are present.

---

### 1. Architecture Overview

```
Engine (singleton)
  ├─ DeviceManager         ← PortAudio device enumeration, buffer size, sample rate
  ├─ PluginManager         ← registers built-in + external plugin types; VST/AU/LV2
  ├─ PluginCache           ← factory for plugin instances by XML type name
  └─ Edit (per project)
       ├─ TransportManager  ← play/pause/record/scrub/loop/position
       ├─ TempoSequence     ← multi-point tempo + time-signature curves
       ├─ KeySequence       ← key/scale changes
       ├─ AudioTrack []
       │    ├─ pluginList    ← ordered effect/instrument chain
       │    ├─ WaveClip []   ← references audio files with offset/loop/warp
       │    └─ MidiClip []   ← note/CC/sysex events with groove quantisation
       ├─ FolderTrack []    ← submix buses
       └─ MarkerTrack / TempoTrack / ChordTrack / VideoTrack …
```

**`te::Engine`** is the root singleton:
```cpp
te::Engine engine { "MyApp", std::make_unique<te::UIBehaviour>(),
                              std::make_unique<te::EngineBehaviour>() };
```

**Edit** lifecycle:
```cpp
auto edit = te::createEmptyEdit (engine, File ("project.tracktionEdit"));
auto edit = te::loadEditFromFile (engine, File ("existing.tracktionEdit"));
edit->save (true, true);
```

---

### 2. Transport

```cpp
auto& transport = edit->getTransport();
transport.play (false);                     // false = don't record
transport.record (false);
transport.stop (false, false);
transport.setCurrentPosition (0.0);        // seconds
transport.setLoopRange ({ 0_tp, 4_tp });   // TimePosition literals
transport.looping = true;
bool isPlaying = transport.isPlaying();
```

**Scrubbing**: `transport.scrub()` moves the playhead at user-controlled speed while maintaining pitch.  
**MTC sync**: incoming MIDI Time Code is decoded and used to slave the transport position.  
**MIDI Clock/MTC output**: engine can send MIDI Clock and MTC to downstream devices.

---

### 3. Tracks and Clips

```cpp
// Tracks
auto track = EngineHelpers::getOrInsertAudioTrackAt (*edit, 0);   // AudioTrack*
auto midiTrack = edit->insertMidiTrack (…);

// Load audio clip
auto clip = track->insertWaveClip (name, audioFile, { timeRange, {} }, false);
clip->setLoopDefaults();                    // use ACID/loop-point metadata

// Create MIDI clip
auto midiClip = midiTrack->insertMidiClip (name, timeRange, nullptr);
midiClip->getSequence().addNote (60, 0.0, 1.0, 100, 0, nullptr); // pitch, time, duration, vel, col, um

// Step Clip (step sequencer)
auto stepClip = track->insertStepClip (timeRange, nullptr);
auto& pattern = stepClip.getPattern (0);   // te::StepClip::Pattern
```

`WaveClip` supports:
- Per-clip pitch/time-stretch (algorithm selectable: Elastique / rubberband / SoundTouch)
- `setSpeedRatio(double)` — playback speed independent of pitch
- `loopInfo` — ACID root note, loop start/end, number of beats, in-key flag
- Warp time points — non-linear time bends within the clip
- `setAutoTempo / setAutoPitch` — conform to Edit's tempo/key automatically

---

### 4. Audio Graph (`tracktion_graph`)

The audio graph is a separate JUCE module (`tracktion_graph`) providing:

- **Multi-CPU node processing**: work queue dispatches independent nodes to a thread pool, maximizing CPU utilization on multi-core machines
- **Automatic PDC** (Plugin Delay Compensation): latency from every plugin is measured and compensated via delay buffers inserted on parallel paths
- **Multiple threading algorithms**: `ThreadPoolStrategy` selectable per platform — real-time-safe work-stealing thread pool vs. sequential (Raspberry Pi)
- **Node types**: AudioNode, MidiNode, ReturnNode, SendNode, SummingNode, LatencyCompensationNode, FreezeNode

Custom plugins integrate via:
```cpp
void applyToBuffer (const PluginRenderContext& fc) override {
    // fc.destBuffer   → AudioBuffer<float>* (read/write)
    // fc.bufferNumSamples → block size this callback
    // fc.midiMessages → MidiBuffer* for MIDI instruments
}
```

---

### 5. Built-in Plugin Suite

#### Synthesis

| Plugin | Description |
|--------|-------------|
| **4OSC** | 4-oscillator subtractive synth; wave shapes: sine/saw/square/triangle/noise; filter (LP/HP/BP), filter ADSR; amp ADSR; unison; chord mode. XML type: `"4osc"` |
| **Sampler** | Per-channel sample playback (`SamplerPlugin`); used by StepClip for drum machines; supports `setSoundMedia(channel, path)` |

**4OSC example preset** (loaded as XML):
```xml
<PLUGIN type="4osc" filterType="1" filterFreq="100" ampAttack="0.0" ampDecay="0.5"
        ampSustain="80" ampRelease="0.3" waveShape1="3">
  <MACROPARAMETERS id="123"/>
  <MODMATRIX/>
</PLUGIN>
```

#### Effects

| Plugin | Algorithm |
|--------|-----------|
| **VolumeAndPan** | Gain + stereo panning |
| **LowPassFilter** | 1-pole IIR lowpass |
| **FourBandEQ** | 4-band parametric EQ (low shelf, two mid peaks, high shelf) |
| **Compressor** | Feed-forward VCA compressor with threshold/ratio/attack/release/makeup |
| **Delay** | Stereo feedback delay with tempo-sync time options |
| **Reverb** | Built-in reverb effect |
| **Chorus** | Stereo chorus |
| **Phaser** | Multi-stage phaser |
| **PitchShift** | Realtime pitch shifting (±24 semitones); parameter: `"semitones up"` |
| **ImpulseResponse** | Convolution reverb via IR file |
| **ToneGenerator** | Multi-waveform test-tone generator |
| **AuxSend / AuxReturn** | Send to / return from a named aux bus |
| **FreezePoint** | Freezes processing upstream of this point to a temp file |
| **Insert** | Hardware insert (send + return to external hardware) |
| **LevelMeter** | Level measurement only (no processing) |
| **PatchBay** | Input/output routing matrix within a rack |

Custom plugin registration:
```cpp
engine.getPluginManager().createBuiltInType<MyPlugin>();
auto instance = edit.getPluginCache().createNewPlugin (MyPlugin::xmlTypeName, {});
track->pluginList.insertPlugin (instance, 0, nullptr);
```

---

### 6. MIDI Features

#### MidiClip

```cpp
auto& seq = midiClip->getSequence();           // te::MidiMessageSequence
seq.addNote (pitch, startBeat, durationBeats, velocity, colour, undoMgr);
seq.addController (controllerType, value, beatPosition, undoMgr);
seq.addSysExEvent (data, beatPosition, undoMgr);
```

**Groove quantisation**: `MidiClip::setGrooveTemplate(GrooveTemplate)` — snaps events to a timing template loaded from a groove file; programmable swing, feel, and strength.

#### StepClip (Step Sequencer)

```cpp
te::StepClip::Pattern pattern = clip.getPattern (0);
pattern.setStep (channel, step, true);    // activate step
auto note = pattern.getNoteNumber (channel); // default MIDI note
pattern.setVelocity (channel, step, 100);
pattern.setGate (channel, step, 0.75f);   // gate length 0–1
```

Up to `StepClip::kMaxNumChannels = 32` channels × configurable steps (default 16) per pattern.

#### Pattern Generator (Algorithmic MIDI)

`PatternGenerator` creates automatic MIDI clips from chord progressions:

- **Mode**: Bass / Melody / Chord / Arp
- **Key**: C–B (12 values)
- **Scale**: major / minor / dorian / mixolydian / pentatonic / etc.
- **Chord progression**: up to 8 chords, each selectable from the scale degrees
- Creates note sequences conforming to the key+scale+mode, timed to the Edit's tempo

---

### 7. Modifiers (Automation Sources)

Beyond static automation curves, every `AutomatableParameter` can be driven by a **Modifier**:

| Modifier | Generates |
|----------|-----------|
| **LFOModifier** | Sine/triangle/square/sawtooth/random waveform at configurable rate (Hz or tempo-sync); depth, phase, offset controls |
| **EnvelopeFollowerModifier** | Follows amplitude of an audio track; attack/release; maps level to parameter range |
| **BreakpointModifier** | Piecewise-linear envelope; arbitrary breakpoints; can loop |
| **StepModifier** | Step-sequencer-style value list; rate in Hz or tempo-sync |
| **RandomModifier** | Smooth random modulation via sample-and-hold or interpolated random walk |
| **MidiTrackerModifier** | Tracks an incoming MIDI CC or note value and maps it to the parameter |

**Macro parameters**: group multiple parameters under a single master knob with configurable ranges per parameter.

**MIDI learn**: `AutomatableParameter::startMidiLearn()` arms the parameter to capture the next incoming CC.

---

### 8. Automation

Automation data is stored per-parameter as `AutomationCurve` — a series of `CurvePoint` values:

```cpp
// Each CurvePoint has { time (double), value (float), curve (float) }
// curve is a Bézier tension: 0 = linear, ±1 = curved
auto& autoParam = *plugin->getAutomatableParameterByID ("gain");
auto& curve = autoParam.getCurve();
curve.addPoint (te::AutomationCurve::CurvePoint { beat, value, 0.0f });
```

Automation recording: while recording, parameter changes are captured into the curve in real-time, then optionally simplified (Douglas-Peucker line simplification) to reduce breakpoint count.

---

### 9. Clip Launching (Non-linear Playback)

```cpp
// Clips can be assigned to launch slots for live performance
clip->setLaunchQuantise (te::ClipLaunchQuantise::nextQNBeat);
clip->launch();     // queues clip to start at next quantise boundary
clip->stop();

// Scenes group clips across tracks for simultaneous launch
auto& scenes = edit->getClipLaunchScenes();
scenes.launch (sceneIndex);
```

Follow actions: after a clip plays its length, automatically trigger another clip by index, stop, loop, return to previous, or trigger randomly.

---

### 10. Time-Stretching and Pitch-Shifting

Time and pitch manipulation in `WaveClip` is provided via three back-end algorithms (configured at compile time through JUCE module flags):

| Backend | Algorithm | Best for |
|---------|-----------|---------|
| `TRACKTION_ENABLE_TIMESTRETCH_SOUNDTOUCH` | WSOLA via SoundTouch | Fast, moderate quality, realtime |
| `TRACKTION_ENABLE_TIMESTRETCH_RUBBERBAND` | Phase vocoder + transient detection (Rubber Band Library) | High quality, offline preferred |
| Elastique (iZotope, commercial) | Phase vocoder, licensed separately | Professional quality |

`clip->setSpeedRatio(double)` — changes playback speed (affects timing but not pitch if `autoTune` is on).  
`clip->setPitchChange(float semitones)` — pitch-shifts independently of speed.  
`clip->setAutoTempo(true)` — stretches to match Edit tempo; `clip->setAutoPitch(true)` — pitch-shifts to match Edit key.

---

### 11. Rendering

```cpp
// Offline render to file
te::Renderer::render (*edit, {
    .destFile      = File ("output.wav"),
    .tracksToDo    = { track1, track2 },
    .bitDepth      = 24,
    .sampleRate    = 44100,
    .normaliseLevel = -0.1f,     // dBFS ceiling, NaN = no normalisation
    .trimSilence   = true
});

// Render specific items
te::Renderer::renderClips ({ clip1, clip2 }, destFile, {});
te::Renderer::renderMidiNote (*note, destFile, { .bpm = 120.0 });
```

Background rendering runs on a dedicated thread and posts progress callbacks. MIDI files can be exported directly from `MidiClip` with SysEx / CC events included.

---

### 12. CHOC Library (`modules/3rd_party/choc/`) — ISC License

**CHOC** (Classy Header-Only Classes) is Tracktion Corporation's standalone header-only utility library (ISC license — permissively usable). It is separately useful without the engine:

#### `choc/audio/choc_SampleBuffers.h` — Multichannel buffer types

```cpp
namespace choc::buffer {
    struct Size { ChannelCount numChannels; FrameCount numFrames; };

    // Non-owning views (interleaved or channel-array layouts):
    InterleavedView<float>     view { data, stride, size };
    ChannelArrayView<float>    chanView { channelPointers, size };

    // Owning allocations:
    InterleavedBuffer<float>   ibuf (2, 1024);
    ChannelArrayBuffer<float>  cbuf (2, 1024);

    // Buffer utilities: copy, add, multiply, mix, clear, trim, iterate
    copyRemappingChannels (dest, source);
    addSamples (dest, source);
    setAllFrames (view, [] { return 0.0f; });
}
```

Template-parameterized on sample type (float/double/int) and layout (interleaved/channel-array). `SampleIterator` with stride lets both layouts be iterated uniformly.

#### `choc/audio/choc_Oscillators.h` — Band-limited oscillators

```cpp
namespace choc::oscillator {
    // All oscillators follow the same interface:
    osc.setFrequency (freq, sampleRate);
    osc.resetPhase();
    auto sample = osc.getSample();

    Sine<float>     sine;      // sin(2π × phase)
    Saw<float>      saw;       // [0,1) → [-1,1] ramp
    Square<float>   square;    // phase > 0.5 ? 1 : -1
    Triangle<float> triangle;  // integrates Square output (Leaky integrator)

    // Batch render to buffer:
    choc::oscillator::render (bufferView, sine);
    choc::oscillator::render<Sine<float>> (bufferView, 440.0, 44100.0);

    auto buf = createBuffer<ChannelArrayBuffer<float>, Sine<float>>(
                   { 2, 1024 }, 440.0, 44100.0);
}
```

`Triangle` uses a leaky-integrator trick: integrate a square wave and periodically re-normalize to prevent DC accumulation.

#### `choc/audio/choc_SincInterpolator.h` — High-quality resampling

```cpp
// Windowed-sinc resampler; numZeroCrossings controls quality (default 50)
choc::interpolation::sincInterpolate<DestBuffer, SourceBuffer, 50> (dest, source);
// Automatically selects up- or down-sampling based on buffer sizes
// For downsampling: applies anti-alias LP filter (band-limiting pass first)
```

The Hann-windowed sinc kernel: $w(x) = \text{sinc}(x) \cdot \frac{1 + \cos(x\pi / N)}{2}$ where $N$ = numZeroCrossings.

#### `choc/audio/choc_MIDI.h` — MIDI utilities

```cpp
namespace choc::midi {
    float noteNumberToFrequency (int note);   // A440_frequency × 2^((note-69)/12)
    float frequencyToNoteNumber (float hz);

    struct NoteNumber {
        uint8_t note;
        uint8_t getChromaticScaleIndex() const;   // 0–11 (C=0)
        int     getOctaveNumber() const;
        float   getFrequency() const;
        std::string_view getName() const;         // "C", "C#", "D" …
        bool    isNatural() const;
        bool    isAccidental() const;
    };

    // ShortMessage (3-byte) and LongMessage types
    // Full byte-level accessors: getType(), getChannel(), getNote(), getVelocity() …
    std::string getControllerName (uint8_t cc);
}
```

#### `choc/audio/choc_MIDISequence.h` — Timestamped MIDI sequence

```cpp
choc::midi::Sequence seq;
seq.addEvent ({ timeStamp, message });           // kept sorted by timestamp
for (auto& e : seq) { /* process e.timeStamp, e.message */ }
seq.iterateEventsInRange (startTime, endTime, [](auto& e) { … });
```

#### `choc/audio/choc_AudioFileFormat.h` — Audio file I/O

Readers/writers for WAV, AIFF, FLAC, OGG, MP3 (decode only), CAF, RIFF64 — header-only, no external deps for WAV/OGG/FLAC.

---

### 13. crill Library (`modules/3rd_party/crill/`) — MIT License

C++ realtime-safe concurrency primitives:

| Header | Primitive | Usage |
|--------|-----------|-------|
| `seqlock_object.h` | `seqlock_object<T>` | Lock-free single-writer multi-reader value (sequence-lock); audio thread reads without blocking |
| `spin_mutex.h` | `spin_mutex` | Busy-wait mutex for very-short critical sections |
| `progressive_backoff_wait.h` | `progressive_backoff_wait` | Yields + sleeps progressively to avoid wasting CPU while waiting |

The seqlock pattern is key for audio thread parameter reading:
```cpp
crill::seqlock_object<PluginParameters> params;
// UI thread:  params.store (newParams);
// Audio thread: auto p = params.load();  // never blocks, always consistent
```

---

### 14. Integration Notes for `rhythm-vibe-mcp`

| Use-case | Relevant tracktion_engine code |
|----------|-------------------------------|
| **Complete DAW data model** | `te::Engine + Edit` — full timeline with tempo, clips, tracks, plugins, automation; GPL/commercial |
| **Custom DSP plugin** | Subclass `Plugin`, override `applyToBuffer(PluginRenderContext&)`; register with `PluginManager::createBuiltInType<T>()` |
| **4-op subtractive synth** | `4OSC` built-in plugin — configurable via XML state; 4 oscillators, filter, ADSRs |
| **Step sequencer** | `te::StepClip + StepClip::Pattern` — per-step gate/velocity/note; up to 32 channels × N steps |
| **Algorithmic MIDI** | `PatternGenerator` — bass/melody/chord/arp from key+scale+chord selection |
| **Parameter modulation** | `LFOModifier`, `EnvelopeFollowerModifier`, `StepModifier`, `RandomModifier` — all attach to any `AutomatableParameter` |
| **Audio buffers (standalone)** | `choc/audio/choc_SampleBuffers.h` — ISC license, no deps; interleaved + channel-array layouts with full math ops |
| **Band-limited oscillators (standalone)** | `choc/audio/choc_Oscillators.h` — ISC; sine/saw/square/triangle templated on float type |
| **High-quality resampling (standalone)** | `choc/audio/choc_SincInterpolator.h` — ISC; windowed sinc, configurable quality |
| **MIDI utilities (standalone)** | `choc/audio/choc_MIDI.h` + `choc_MIDISequence.h` — ISC; note↔freq, named notes, sorted event sequence |
| **Audio file I/O (standalone)** | `choc/audio/choc_AudioFileFormat.h` — ISC; WAV/FLAC/OGG/MP3 without external deps |
| **Realtime-safe objects (standalone)** | `crill/seqlock_object.h` — MIT; lock-free parameter transfer between UI and audio threads |
