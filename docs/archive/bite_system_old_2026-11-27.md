# Bite System — Jaws Unleashed

The bite interaction system is fully component-based, as revealed by the property reflection metadata in the CLAS chunk. The engine supports per-limb bite targeting, material swapping on impact, skeletal replacement for dismemberment, and nutrition/damage scaling per target type.

---

## NABiteTarget — Core Component

The `NABiteTarget` class defines any object the shark can bite. All properties are reflected in the CLAS chunk.

| Property | Meaning |
|---|---|
| `m_hp` | Hit points for this bite target |
| `m_damagemultiplier` | Damage scaling factor |
| `m_nutrition` | Nutrition gained by shark when this target is eaten |
| `m_radius` | Collision radius for bite detection |
| `m_eattype` | Category of object (creature, object, vehicle, etc.) |
| `m_creature` | Associated creature reference |
| `m_dragfactor` | How much this object resists being dragged/thrown |
| `m_shakefactor` | Camera/feedback shake intensity on bite |
| `m_bitetargetmodel` | Model displayed while being bitten |
| `m_bitetargetmaterialindex` | Material swap index triggered on bite impact |
| `m_dependentlimbs` | Other `NABiteTarget` components that are destroyed when this one is |
| `m_rubberskeletonid` | Replacement skeleton ID for ragdoll/dismemberment |

**Implications:**
- Each limb (head, torso, arm, etc.) is a separate `NABiteTarget` component
- Biting a limb can trigger material swaps (blood effects, wound textures)
- `m_dependentlimbs` creates a destruction chain — destroying one part destroys attached parts
- `m_rubberskeletonid` drives the skeletal swap from animation skeleton to ragdoll skeleton

---

## NAChewingToy — Physics-Enabled Prey

Objects the shark can grab, drag, and throw are `NAChewingToy` components.

| Property | Meaning |
|---|---|
| `m_velocity` | Initial velocity when grabbed |
| `m_angularvelocity` | Rotational velocity when thrown |
| `m_gravity` | Physics gravity scale |
| `m_attackgroups` | Collision group mask for attack interactions |
| `m_sensorgroups` | Sensor mask for detection |
| `m_target` | Target reference |

---

## Dismemberment Framework

The anatomy/dismemberment system uses standard body-part property naming across all creature types:

| Property | Body Part |
|---|---|
| `m_head` | Head |
| `m_body` | Torso / body |
| `m_leftarm` | Left arm |
| `m_rightarm` | Right arm |
| `m_leftleg` | Left leg |
| `m_rightleg` | Right leg |
| `m_lefthand` | Left hand |
| `m_righthand` | Right hand |
| `m_leftfoot` | Left foot |
| `m_rightfoot` | Right foot |

Supporting system properties:
- `m_dependentlimbs` — destruction chain references
- `m_rubberskeleton` — ragdoll skeleton binding
- `m_dismembermaterialindex` — material shown at dismemberment point (wound texture)

---

## Group-Based Interaction Filtering

The engine uses bitmask groups to control which objects can interact with which:

| Property | Purpose |
|---|---|
| `m_attackgroups` | Which groups this object can attack |
| `m_sensorgroups` | Which groups this object can detect |
| `m_backgroundgroups` | Background collision groups |

This acts as a layer system for collision, AI targeting, and bite interactions — allowing the shark, prey, and environment to each occupy different channels.

---

## Hierarchy Example (Hammerhead)

Reconstructed from BRTR CHBR nodes and property reflection:

```
Hammerhead SkeletonModel
├── Hammerhead Head Fixed Brick     [NABiteTarget: m_hp, m_nutrition, m_dependentlimbs]
├── Hammerhead Body Fixed Brick     [NABiteTarget: primary hp pool]
└── Hammerhead Tail Fixed Brick     [NABiteTarget: m_dependentlimbs → body]
```

Spatial layouts extracted from transform matrices match expected anatomy — confirmed via world-space AABB comparison.

---

## Known Placed Bite Targets (FISH.GDW)

Notable objects with mesh references in the FISH.GDW BRTR scene graph:

- `GWside` — Great White Shark model
- `WhaleCarcass Body` — Dead floating whale (edible)
- `MartinWalker` — NPC with bite target components
- `mansionC` (×2) — Underwater buildings (structural bite targets)
- `Torheto_pozna` — Breakable posts (Hungarian: "breakable post")
