# Writing a scene

*The spec format, field by field. How to build geometry a video model can read
is [craft/modelling.md](craft/modelling.md); how to run the commands that consume
this is [usage.md](usage.md).*

## The file

```jsonc
{
  "fps": 24,
  "duration": 5.0,              // seconds
  "resolution": [960, 540],     // blockout only; final resolution is in `generation`

  "objects": [
    {
      "name": "hero",
      "type": "cube",           // cube | plane | sphere | cylinder | cone | torus
      "size": 2.0,
      "location": [0, 0, 1.0],  // metres, Z-up
      "rotation": [0, 0, 0],    // degrees, XYZ
      "animation": {
        "rotation": [
          { "t": 0.0, "value": [0, 0, 0], "ease": "ease" },
          { "t": 5.0, "value": [0, 0, 120] }
        ]
      }
    }
  ],

  "camera": {
    "lens": 35.0,               // mm, on a 36mm sensor
    "location": [9, -9, 5],
    "look_at": [0, 0, 1.0],     // aim point, not a rotation — far easier to author
    "animation": { "location": [ ... ], "look_at": [ ... ] }
  },

  // `generation` is shown here because it is what a merged spec looks like.
  // Author it in shot.json -- see above.
  "generation": {
    "prompt": "A polished dark-granite monolith rotating in a brutalist hall...",
    // ...or "full_prompt", sent byte for byte with no contract prepended
    "reference_mode": "video",  // video | frames | first
    "duration": 5,              // 4-30
    "resolution": "720p",       // 480p | 720p; 1080p on seedance-2 only
    "aspect_ratio": "16:9",
    "model": "seedance-2-fast",
    "generate_audio": true,     // default; false for a silent clip
    "style_references": [       // look references, in tag order: @image1, @image2 ...
      "styleframes/lookref_a.png",
      "styleframes/lookref_b.png"
    ]
  }
}
```

Animatable channels: `location`, `rotation`, `scale`, plus `look_at`, `lens`,
`roll`, `pan` and `tilt` on the camera.

## Assets and instances

Repeated geometry goes in `projects/<proj>/assets/<name>.json` and is placed by
an `instances` list:

```jsonc
"instances": [
  { "asset": "sedan", "name": "car_01", "location": [5.9, -104, 0], "size": [1.9, 4.6, 1.5] },
  { "asset": "sedan", "name": "car_06", "location": [-1.7, -52, 0], "size": [2.1, 5.6, 1.8],
    "rotation": [0, 0, 180] }
]
```

An asset declares its parts **in the unit space of its own bounding box**: `x`
and `y` as fractions of width and length from the centre, `z` as a fraction of
height up from the ground, `scale` as fractions of all three. Radii and depths
are fractions too — `size` follows height and `depth` follows width, which is
what a wheel wants. The instance supplies the footprint, so a saloon and a van
come out of one recipe at their own proportions.

This is what "version the recipe, not the result" means in practice. Eight cars
of eight primitives went into the NYC shot as **64 objects with the rule thrown
away**; changing the windscreen rake meant editing 64 blocks. They are now eight
lines and one asset file, and the rake is one number in one place.

`rotation` on an instance is a turn about Z and nothing else. That is a real
constraint, not an omission: a yaw folds exactly into each part's own XYZ euler,
where a general rotation would need composing, and a wrong composition is
invisible in a grey render and obvious in the result.

A part can also be a **`mesh`**, with `vertices` and `faces` placed by hand in
the same unit space. That is how a shape that must change with the footprint
gets built: a windscreen raked 34.8° on a 4.6 m car should be 34.4° on a 5.6 m
one, because the rake is rise over run — a stored angle on a rotated box cannot
know that, and vertices get it for free.

`assets/sedan.json` and `assets/sedan_solid.json` are the same car built both
ways, and `assets/car_compare.json` renders them side by side at three
footprints. Six parts instead of eight, no panels overlapping a roof box, and
the rake correct at every size.

Expansion happens once, when the spec is loaded, so Blender, `audit` and `check`
all measure the same geometry — and `scene_id` hashes the expansion, because
editing an asset changes the shot and an id that ignored it would call two
different shots the same one.

`look_at` aims the camera; the three angles rotate it about its own axes
afterwards, in degrees. `roll` banks it — without that a flight reads as a drone
holding the horizon level. `pan` and `tilt` swing the aim off the target, which
is how a subject gets to sit anywhere but dead centre. All three default to 0,
so a scene that omits them renders exactly as before.

Easing is set per keyframe and governs the segment *starting* at that key:
`ease` (smoothstep, the default), `linear`, `in`, `out`, `smooth`.

`smooth` is the one to reach for on a move that should not stop. The other four
shape one segment in isolation and know nothing about their neighbours — `ease`
in particular has zero velocity at *both* ends, so a run of eased keys arrives
and halts at every one of them, and `linear` turns a corner at each key instead
of curving through it. `smooth` takes its tangent at a key from the keys either
side, so velocity carries through: continuous speed, a curved path, and speed
still steered by how far apart the keys are. With only two keys it is exactly
linear.

**Write the prompt about materials and light, not about layout.** The provider
prepends the reference contract itself. Everything spatial — blocking, framing,
camera path — comes from the blockout; the prompt's job is only to say what the
surfaces are made of and how they are lit.

`style_references` are paths relative to the shot directory, and **order is
meaning**: the first becomes `@image1`. When any are present the contract adds
the sentence that decides the shot — *appearance is determined solely by the
images* — and tells the model to take no framing from them. Repeated `--style`
flags override the list for one run without editing the scene, and a
`styleframe.png` sitting in the take is the last resort.

**`full_prompt` opts out of all of that.** It is sent byte for byte, contract
included, and it exists because an assembled prompt is worth less than a tested
one. The NYC shot's prompt was written by hand, run, and judged good; rebuilding
a near-miss of it every time would swap a tested string for an untested one. Use
`prompt` while a look is still being found, and move to `full_prompt` once a
particular wording is the reason a take works.

`check` guards the one thing a verbatim prompt can get wrong on its own: naming
`Image 3` when only two references will be attached. That fails before anything
is uploaded.
