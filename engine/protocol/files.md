# Files: where every video file lives, and how a video moves from first draft to final and back

`vs protocol files` prints this. The kit names every file and folder; nobody types a file name. Each rule below is
enforced by a command (named in brackets), never by an agent remembering it.

## The words

- **video**: one piece, under one name, in one project: `studio/projects/<video>/`. The folder name IS the video's
  name: every file the video produces carries it. A name is lowercase words joined by hyphens (`launch-teaser`).
- **shape**: `vertical` (1080×1920, phones) or `widescreen` (1920×1080). A video can have both. A shape is a property
  of the picture: filing reads each file's real width and height, and refuses a file whose pixels disagree with its
  name. (The review diary keeps them as cuts `9x16` / `16x9`; file and folder names always use the words.)
- **draft**: any render you haven't called done. **version** (`v1`, `v2` …): one per render; never reused, never
  overwritten. Both shapes of one version share its number.
- **final**: a version the human called done. **latest**: the newest final of each shape.

## The folders

```
studio/
  projects/<video>/                       one folder per video; both shapes live here
    video.json                            where the video stands (the kit writes it: never by hand)
    plan.json | reel.json, scenes.js …    the sources (reel.json "shapes" holds what differs per shape)
    drafts/
      v8/
        <video>-vertical-v8.mp4           the render
        <video>-vertical-v8-take2.mp4     a mix of it (take2 = music take 2; -sfx, -mixed)
        <video>-vertical-v8-cover.jpg
        <video>-widescreen-v8.mp4         the other shape, same version
        data/vertical/ data/widescreen/   the kit's own files for each render: timing, element map, findings,
                                          qa, cues, the composition, and the sources that made it (source/)
      watched/                            Review Studio's copies of what each round showed
    review/                               the review diary (log.jsonl), its snapshot, the note stills
    build/                                regenerated; safe to delete
  finals/<video>/                         every version called done, both shapes
    <video>-vertical-v8.mp4  <video>-vertical-v8-cover.jpg
    <video>-widescreen-v8.mp4  <video>-widescreen-v8-cover.jpg
  latest/<video>/                         only the newest final of each shape, no version in the name
    <video>-vertical.mp4  <video>-vertical-cover.jpg
    <video>-widescreen.mp4  <video>-widescreen-cover.jpg
  latest/VERSIONS.md                      which version each latest file is, and when it was filed
  archive/                                project folders a restructure retired (nothing reads them)
```

Folders organize; names identify. A file dragged out of its folder still says which video, shape and version it is.
`finals/` and `latest/` hold only videos and covers. `latest/` is rebuilt from `finals/` (clones: no extra space).

## The happy path

```
vs new <video> --kind explainer|reel --shape vertical|widescreen
   │   status: first          (the first shape: drafts v1, v2 … in Review Studio)
   ▼
human approves the first shape  →  vs shape <the other>
   │   status: second         (the other shape, built at the approved version; the same Review Studio page,
   ▼                           Vertical | Widescreen switch at the top, one address, one port)
human approves both  →  vs finish
   │   status: done           (finals/<video>/ gets both shapes; latest/<video>/ is replaced; the page says Done)
   ▼
later: "let's edit <video>"  →  vs reopen <video>
       status: first again    (the sources go back to exactly what made the last final; the next draft is
                               last + 1; the loop repeats; vs finish files it and it replaces latest/)
```

`vs status` says where a video stands and the one next step, every time. Read it whenever unsure.

## What the kit refuses (and the way around it)

| it refuses | why | the way around, for a real pivot |
|---|---|---|
| a render of a finished video [vs build] | a final is done; a change starts a new version | `vs reopen <video>` |
| the second shape before the first is approved [vs shape, vs build] | the second shape copies an approved picture | `--early "<why>"` (logged in video.json) |
| filing a final over a different file of the same name [vs finish] | finals are never overwritten | nothing: it's always a kit bug |
| filing a file whose pixels aren't its shape [vs finish] | the name must tell the truth | nothing: rename by rebuilding |
| finishing before every shape in the round is approved [vs finish] | done means approved | `--one-shape` for a video made in one shape only |
| a second Review Studio server for the same video [vs review launch] | one video, one page, one port | none needed: both shapes are on the one page |

A pivot is allowed; it is never silent. Every `--early` / `--one-shape` lands in `video.json → log` with its reason.

## Reopening a final

`vs reopen <video>` finds the newest final in `video.json`, and compares the project's sources (reel.json, plan.json,
scenes.js, cues.py, narration.txt, SCRIPT.md, music.json, sfx.json, mix.json) with the copy kept beside that final's
render (`drafts/vN/data/<shape>/source/`). If anything changed after the final, the current files are set aside in
`drafts/reopened-<date>/` first, then the final's are put back. The version becomes last + 1, the shape the video
started in is the one being built, and status is `first`. Nothing is deleted.

## Old drafts

Drafts are never deleted by a step. A finished video's drafts can be large (a few GB); clearing them is the human's
call, per video.
