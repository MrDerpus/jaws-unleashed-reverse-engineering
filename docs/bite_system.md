# Biting and body parts

**In short:** anything the shark can bite carries an `NABiteTarget` component, with its own hit points, nutrition, size and damage multiplier.
- Each body part is its own target.
- Biting one can swap its material (wounds), destroy dependent parts and swap in a ragdoll skeleton.
- Things the shark can grab and throw are `NAChewingToy`s.
- Group bitmasks decide what can attack or sense what.

Most of this comes from field names. The bite damage itself (frames and formula) is decoded from the exe: `docs/exe_analysis.md` §6 "Bite animation".

Rewritten for readability on 2026-11-27. Old version: `docs/archive/bite_system_old_2026-11-27.md`.

---

## Contents

1. [`NABiteTarget`](#1-nabitetarget)
2. [`NAChewingToy`](#2-nachewingtoy)
3. [Body parts and dismemberment](#3-body-parts-and-dismemberment)
4. [Interaction groups](#4-interaction-groups)
5. [How the bite deals damage](#5-how-the-bite-deals-damage)
6. [Examples](#6-examples)

---

## 1. `NABiteTarget`

| Field | Probably |
|---|---|
| `m_hp` | Hit points |
| `m_damagemultiplier` | Damage scaling |
| `m_nutrition` | Hunger the shark regains by eating it |
| `m_radius` | Bite detection radius |
| `m_eattype` | Category (creature, object, vehicle, …) |
| `m_creature` | The creature it belongs to |
| `m_dragfactor` | Resistance to being dragged or thrown |
| `m_shakefactor` | Shake on bite |
| `m_bitetargetmodel` | Model shown while bitten |
| `m_bitetargetmaterialindex` | Material swapped in on a bite |
| `m_dependentlimbs` | Other targets destroyed along with this one |
| `m_rubberskeletonid` | Ragdoll skeleton swapped in on dismemberment |

**What it allows:**
- Each limb (head, torso, arm…) is a separate target.
- A bite can swap a material (blood, wound textures).
- `m_dependentlimbs` chains destruction: losing one part loses the parts attached to it.
- `m_rubberskeletonid` swaps the animation skeleton for a "rubber" ragdoll one (`docs/animation_system.md` §8).

---

## 2. `NAChewingToy`

Things the shark can grab, drag and throw.

| Field | Probably |
|---|---|
| `m_velocity` | Velocity when released |
| `m_angularvelocity` | Spin when thrown |
| `m_gravity` | Gravity scale |
| `m_attackgroups` | Attack mask |
| `m_sensorgroups` | Sensor mask |
| `m_target` | Target |

---

## 3. Body parts and dismemberment

The same field names appear across creature types:

| Field | Part |
|---|---|
| `m_head` | Head |
| `m_body` | Torso |
| `m_leftarm`, `m_rightarm` | Arms |
| `m_lefthand`, `m_righthand` | Hands |
| `m_leftleg`, `m_rightleg` | Legs |
| `m_leftfoot`, `m_rightfoot` | Feet |

**Supporting fields:**
- `m_dependentlimbs`: the destruction chain;
- `m_rubberskeleton`: the ragdoll skeleton;
- `m_dismembermaterialindex`: the material at the cut (wound texture).

Spawn templates for loose parts (`BloodyHead`, `BloodyLeftArm`, …) sit at the origin in the open-ocean levels (`docs/terrain_and_water_bounds.md` §5).

---

## 4. Interaction groups

| Field | Probably |
|---|---|
| `m_attackgroups` | Which groups this object can attack |
| `m_sensorgroups` | Which groups it can detect |
| `m_backgroundgroups` | Background collision groups |

- Bitmask layers for collision, AI targeting and biting.
- **In the exe:** a brick's attack and sensor masks are at `+0x3C` / `+0x40`. The collision pair test (`0x695F30`) checks `mask & a[+0x3C] & b[+0x40]` (`docs/exe_analysis.md` §5).

---

## 5. How the bite deals damage

Decoded from the exe (`docs/exe_analysis.md` §6 "Bite animation"):
- **The bite clip** `Shark_GW_Pitbull04` is the grab-chew-shake. It deals damage at three frames (start +12, +23, +33); shorter variants deal two.
- **Damage** = `(SharkConfig[0xD74] × Power ability + 1) × SharkConfig[0x4AC]`, sent to the held prey as message `0x27`.
- **Shake/tear** (sub-state `0xF`) deals damage by how far the shark moves instead (`Razas damage!`).

---

## 6. Examples

### Hammerhead

From the `BRTR` nodes and field names:

```
Hammerhead SkeletonModel
├── Hammerhead Head Fixed Brick     NABiteTarget: m_hp, m_nutrition, m_dependentlimbs
├── Hammerhead Body Fixed Brick     NABiteTarget: the main hit-point pool
└── Hammerhead Tail Fixed Brick     NABiteTarget: m_dependentlimbs → body
```

The parts' world bounding boxes match the expected anatomy.

### Notable placed objects in FISH

Not each one checked for a bite target:
- `GWside`: the great white (the player's own model);
- `WhaleCarcass Body`: the floating dead whale (edible; SC17);
- `MartinWalker`: an NPC with bite-target parts;
- `mansionC` ×2: underwater buildings;
- `Torheto_pozna`: breakable posts (*törhető pózna*).
