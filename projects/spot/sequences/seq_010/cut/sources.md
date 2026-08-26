# What is in the cut

Assembled by hand with ffmpeg's concat demuxer, stream-copied rather than
re-encoded: all previews come out of the same Blender render settings, so there
is nothing to normalise and re-encoding would only spend a generation of quality
to arrive back where it started.

**This file is the point of the folder.** A cut is the one artefact here that
cannot be re-derived from a scene spec, because it depends on *which take* of
each shot went into it — and the scene ids in those filenames are the only
record of that. Rebuild the cut and this table moves with it, or the file stops
saying what it is.

## `seq_010_cut_v002.mp4` — current

264 frames, 11.000 s, 960x540 @ 24 fps.

| Shot | Frames | Source |
| --- | --- | --- |
| 1 | 72 | `sh_0010/preview/seq_010_sh_0010_deck_a_9c6fab_preview_v014.mp4` |
| 2 | 60 | `sh_0020/preview/seq_010_sh_0020_door_a_7254f1_preview_v006.mp4` |
| 2b | 60 | `sh_0025/preview/seq_010_sh_0025_face_a_03e136_preview_v006.mp4` |
| 3 | 72 | `sh_0030/preview/seq_010_sh_0030_exit_a_9a432e_preview_v003.mp4` |

Adds `sh_0025`, the full-face insert, between the door and the departure. Shots
1 and 2 are re-renders of the same staging: the figure asset's neck was rebuilt
for that insert, and it is shared, so their scene ids moved even though nothing
was reframed. Shot 3 kept its id — no figure in it, no geometry change.

## `seq_010_cut_v001.mp4` — superseded

204 frames, 8.500 s. Three shots, before the face insert existed.

| Shot | Frames | Source |
| --- | --- | --- |
| 1 | 72 | `sh_0010/preview/seq_010_sh_0010_deck_a_232596_preview_v013.mp4` |
| 2 | 60 | `sh_0020/preview/seq_010_sh_0020_door_a_14303e_preview_v005.mp4` |
| 3 | 72 | `sh_0030/preview/seq_010_sh_0030_exit_a_9a432e_preview_v002.mp4` |
