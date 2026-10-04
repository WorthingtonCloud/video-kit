// The round's panel as a whole, after every part has drawn its own: each section shows when it has something, its count
// is what's waiting for you there, and the top line's Inbox says how many things want you in all.
import { app, $ } from "./core.js";

export const panel = {
  maps() {
    panel.render();
  },
  render() {
    if (!app.state) return;
    let total = 0;
    for (const id of ["sec-fixes", "sec-asks", "sec-notes"]) {
      const sec = $(`#${id}`),
        todo = sec.querySelectorAll("[data-todo]").length,
        any = sec.querySelector(".res, .item");
      if (id !== "sec-notes") sec.hidden = !any;
      sec.querySelector(":scope > .k em").textContent = id === "sec-notes" ? sec.querySelectorAll(".item").length || "" : todo || "";
      if (id !== "sec-notes") total += todo;
    }
    $("#todo").textContent = total || "";
    $("#roundbtn").title = total ? `This round: ${total} thing${total === 1 ? "" : "s"} waiting for you` : "This round: nothing waits for you";
    $("#dtabn").textContent = total ? `· ${total} for you` : "";
  },
};
