// The loop, the same every round: give feedback → review it → approve & send → tell Claude → Claude's turn. Everything
// the human does in a round (a note, an answer, a pick, a mix, approving the video) waits here, held, with Undo, until
// the Review list is approved and sent; then one word for the chat, unless Claude is watching (vs review wait), when
// the send itself wakes it. The page knows Claude has it when vs review show
// reads it. A note added after a send starts the next batch, with its own send.
import { app, $, post, undo, pending, esc, round, toast } from "./core.js";
import { player } from "./player.js";

// step 4 is the human's only while Claude isn't watching (vs review wait): watching, a send reaches it on its own
const STEPS_TELL = ["Give feedback", "Review it", "Approve & send", "Tell Claude", "Claude's turn"],
  STEPS_AUTO = ["Give feedback", "Review it", "Approve & send", "Claude picks it up", "Claude's turn"];
// the top bar has room for one word a step (a reviewer, Oct 4, 2026: "too crowded… maybe one word will do"); the full words
// stay in each step's tooltip and in the Sent dialog's line
const SHORT = { "Give feedback": "Feedback", "Review it": "Review", "Approve & send": "Send", "Tell Claude": "Tell", "Claude picks it up": "Received", "Claude's turn": "Claude" };
// a send Claude already read needed no telling either (the watcher exits once it reads)
const steps4 = () => {
  const R = round();
  return app.ctx?.waiting || (R?.sends && (R.read_sends || 0) >= R.sends) ? STEPS_AUTO : STEPS_TELL;
};
const clock = (at) => new Date(at).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
let editing = null; // the note whose words are being changed in the Review list

// where this round is in the loop (1–5)
export function step() {
  const R = round();
  if (!R || R.status === "closed") return 5;
  if (!$("#review-sheet").hidden) return 2;
  if (R.sends && !pending().length) return (R.read_sends || 0) >= R.sends ? 5 : 4;
  return 1;
}

function loopLine() {
  const n = step();
  $("#loop").innerHTML = steps4().map((w, i) => `<li class="${i + 1 < n ? "past" : i + 1 === n ? "now" : ""}" title="${i + 1}. ${esc(w)}"><span class="dot"></span><span class="w">${esc(SHORT[w] || w)}</span></li>`).join("");
}

// the button at the bottom of the round's panel: how much is waiting, and what happens next
function sendButton() {
  const R = round(),
    k = pending().length,
    b = $("#send"),
    p = $("#sendp");
  // nothing to change, never sent yet: one click says so (the send still reaches Claude, and its watch wakes on it)
  const none = !!R && R.status !== "closed" && !k && !R.sends;
  b.disabled = !R || R.status === "closed" || (!k && !none);
  b.dataset.none = none ? "1" : "";
  b.textContent = k ? `Review & send · ${k} thing${k === 1 ? "" : "s"}` : none ? "No notes · send" : "Review & send";
  p.textContent = !R
    ? "No round open: Claude opens one on a rendered version."
    : R.status === "closed"
      ? "This round is closed."
      : k
        ? "Nothing reaches Claude until you send it."
        : R.sends
          ? (R.read_sends || 0) >= R.sends
            ? `Claude has it (read ${clock(R.read)}). Anything new waits here for its own send.`
            : app.ctx?.waiting
              ? "Sent: Claude is watching and picks it up on its own. Anything new waits here for its own send."
              : "Sent: tell Claude “sent” in chat. Anything new waits here for its own send."
          : "Nothing to change? “No notes · send” tells Claude so.";
}

// ── step 2: the Review list ──
function review() {
  const R = round(),
    L = pending();
  $("#rv-k").textContent = R ? `Round ${R.n} · v${R.version} · step 2 of the loop` : "";
  $("#rv-list").innerHTML = L.length
    ? L.map((s) => {
        const note = s.kind === "note.added" && s.note && app.state.notes[s.note];
        return `<li data-seqs="${s.seqs.join(",")}"><time>${esc(clock(s.at))}</time><div class="what"><b>${esc(s.text)}</b>
          ${editing === s.note && note ? `<textarea rows="2" data-edit="${esc(s.note)}">${esc(note.comment || "")}</textarea><div class="acts" style="margin-top:6px"><button data-rv="cancel">Cancel</button><button class="primary" data-rv="save" data-note="${esc(s.note)}">Save</button></div>` : ""}</div>
          <span class="acts">${note && editing !== s.note ? `<button data-rv="edit" data-note="${esc(s.note)}">Change</button>` : ""}<button data-rv="undo">Undo</button></span></li>`;
      }).join("")
    : `<li><span></span><div class="what"><b>Nothing yet.</b><br><span class="dhint">If this version is fine as it is, approve it. If not, leave a note.</span></div><span></span></li>`;
  $("#rv-send").disabled = !L.length;
  $("#rv-send").textContent = L.length ? `Approve & send ${L.length} thing${L.length === 1 ? "" : "s"} to Claude` : "Approve & send to Claude";
}
export function openReview() {
  if (player.playing()) player.pause();
  editing = null;
  $("#review-sheet").hidden = false;
  review();
  loopLine();
  $("#rv-send").focus();
}
function closeReview() {
  $("#review-sheet").hidden = true;
  loopLine();
}
$("#send").onclick = async () => {
  if ($("#send").dataset.none) await post([{ type: "round.nonotes", round: round().n }], { quiet: true });
  openReview();
};
$("#rv-back").onclick = closeReview;
$("#rv-list").addEventListener("click", async (e) => {
  const b = e.target.closest("button[data-rv]");
  if (!b) return;
  const r = b.dataset.rv;
  if (r === "undo") await undo(b.closest("li").dataset.seqs.split(",").map(Number));
  else if (r === "edit") {
    editing = b.dataset.note;
    review();
    $("#rv-list [data-edit]")?.focus();
  } else if (r === "cancel") {
    editing = null;
    review();
  } else if (r === "save") {
    const t = $("#rv-list [data-edit]"),
      text = t.value.trim();
    editing = null;
    await post([{ type: "note.edited", id: b.dataset.note, comment: text }], { quiet: true });
    toast("Changed.");
  }
  review();
});

// ── step 3 → 4: send it, then one word for the chat ──
$("#rv-send").onclick = async () => {
  const R = round(),
    k = pending().length;
  await post([{ type: "round.sent", round: R.n }]);
  closeReview();
  const S = round();
  $("#st-word").textContent = S.sends > 1 ? "sent again" : "sent";
  $("#st-sum").textContent = `Claude reads exactly what you approved: ${k} thing${k === 1 ? "" : "s"}. While Claude works, you can keep watching.`;
  $("#sent-sheet").hidden = false;
  sentSheet();
};
function sentSheet() {
  const R = round();
  if (!R || $("#sent-sheet").hidden) return;
  const n = step();
  // once Claude has read the send, the watcher has exited: that's done, not a cue to go type "sent"
  const read = (R.read_sends || 0) >= R.sends,
    auto = !!app.ctx?.waiting || read;
  $("#st-h").textContent = read
    ? "Sent. Claude has it."
    : auto
      ? "Sent. Claude picks it up on its own."
      : "Sent. Now tell Claude in chat.";
  $("#st-tell").hidden = auto;
  $("#st-loop").innerHTML = steps4().map((w, i) => `<span class="${i + 1 === Math.max(4, n) ? "now" : ""}">${esc(w)}</span>`).join("");
  $("#st-turn").classList.toggle("ok", read);
  $("#st-turn-t").textContent = read ? `Claude read it at ${clock(R.read)}. The next version opens here when it's ready.` : "Waiting for Claude to read it.";
}
$("#st-copy").onclick = () => {
  const w = $("#st-word").textContent;
  navigator.clipboard?.writeText(w).then(() => toast("Copied: paste it in the chat."), () => {
    getSelection().selectAllChildren($("#st-word"));
    toast("Selected: press ⌘C.");
  });
};
$("#st-ok").onclick = () => ($("#sent-sheet").hidden = true);

// ⌘Z: take back the last thing that's waiting (never while typing: the box has its own undo)
document.addEventListener("keydown", (e) => {
  if ((e.metaKey || e.ctrlKey) && !e.shiftKey && e.key.toLowerCase() === "z" && !e.target.closest?.("textarea, input")) {
    const last = pending().at(-1);
    if (last) {
      e.preventDefault();
      undo(last.seqs);
    }
  } else if (e.key === "Escape" && !$("#review-sheet").hidden) {
    e.stopPropagation();
    closeReview();
  } else if (e.key === "Escape" && !$("#sent-sheet").hidden) {
    e.stopPropagation();
    $("#sent-sheet").hidden = true;
  }
}, true);

export const loop = {
  render() {
    loopLine();
    sendButton();
    if (!$("#review-sheet").hidden && !document.activeElement?.dataset?.edit) review();
    sentSheet();
  },
};
