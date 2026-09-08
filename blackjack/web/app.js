"use strict";
const $ = id => document.getElementById(id);
let state = null, busy = false;
const signed = (n, digits=4) => (n > 0 ? "+" : "") + n.toFixed(digits);
const title = x => x[0].toUpperCase() + x.slice(1);
function cards(node, ranks, hidden=false) {
  node.replaceChildren();
  for (const rank of [...ranks, ...(hidden ? [null] : [])]) {
    const card = document.createElement("span"); card.className = "card" + (rank === null ? " back" : "");
    card.textContent = rank === null ? "♠" : rank === 1 ? "A" : rank;
    card.setAttribute("aria-label", rank === null ? "Hidden dealer card" : String(card.textContent)); node.append(card);
  }
}
function controls() {
  document.querySelectorAll("button,input,select").forEach(n => n.disabled = busy);
  $("deal").disabled = busy || (state && state.status !== "settled");
  document.querySelectorAll("[data-action]").forEach(n => {
    n.disabled = busy || !state?.analysis?.actions.some(a => a.action === n.dataset.action);
    n.classList.toggle("best", !!state?.analysis?.optimal_actions.includes(n.dataset.action));
  });
}
function render(r) {
  state = r;
  $("round").textContent = `Round ${r.round}${r.reshuffled ? " · New shuffle" : ""}`;
  $("shoe").textContent = `${r.dealt} / 312 cards dealt`;
  cards($("dealer-cards"), r.dealer, !r.revealed);
  const raw = r.dealer.reduce((a,b)=>a+b,0);
  $("dealer-total").textContent = r.revealed ? String(raw + (r.dealer.includes(1) && raw<=11 ? 10 : 0)) : "· hole card hidden";
  $("hands").replaceChildren();
  r.hands.forEach((h,i) => {
    const block = document.createElement("div"); block.className = "hand" + (i === r.active && r.status === "playing" ? " active" : "");
    const heading = document.createElement("h2"); heading.textContent = `${r.hands.length>1 ? "Hand " + (i+1) : "Your hand"} · ${h.total}`;
    const row = document.createElement("div"); row.className = "cards"; cards(row,h.cards);
    const note = document.createElement("small"); note.textContent = `${h.wager} unit${h.wager>1 ? "s" : ""}${h.done ? " · Finished" : i===r.active ? " · Playing" : " · Waiting"}`;
    block.append(heading,row,note); $("hands").append(block);
  });
  $("draw-form").hidden = !r.pending;
  $("actions").hidden = r.status !== "playing" || !!r.pending;
  $("next").hidden = r.status !== "settled";
  $("values").replaceChildren();
  if (r.analysis) {
    $("suggestion").textContent = `Suggested: ${r.analysis.optimal_actions.map(title).join(" / ")}`;
    $("ev").textContent = `EV ${signed(r.analysis.value)}`;
    $("hint").textContent = `${r.analysis.label}. Choose an action below.${r.hands.length>1 ? " EV is for this hand only." : ""}`;
    for (const a of r.analysis.actions) {
      const tr=document.createElement("tr");
      for(const value of [title(a.action),signed(a.ev),signed(a.baseline_ev)]) {const td=document.createElement("td");td.textContent=value;tr.append(td);}
      $("values").append(tr);
    }
  } else if (r.pending) {
    $("suggestion").textContent = r.pending === "split-card" ? `Deal to hand ${r.active+1}` : `${title(r.pending)}: add a card`;
    $("ev").textContent = "";
    $("hint").textContent = "Draw from the shoe, or enter the card you received.";
    $("draw-label").textContent = r.pending === "split-card" ? `Second card for hand ${r.active+1}` : "Your next card";
  } else {
    $("suggestion").textContent = r.result.message;
    $("ev").textContent = `Result ${signed(r.result.profit,2)} units`;
    $("hint").textContent = (r.threshold === null || r.dealt >= r.threshold) ? "The shoe and count will reset before the next round." : "Next round continues the same shoe and count.";
  }
  $("count").textContent = `Hi-Lo count ${signed(r.count.running,0)} · True count ${signed(r.count.true,2)} · ${r.count.visible} visible`;
  $("profit").textContent = `Session profit: ${signed(r.profit,2)} units`;
  controls();
}
async function send(extra={}, fresh=false) {
  if (busy) return;
  busy=true; controls(); $("error").hidden=true;
  const p={method:$("method").value,...extra};
  if(state && !fresh) {p.game_id=state.game_id;p.revision=state.revision;}
  try {
    const response=await fetch("/api/play",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(p)});
    const r=await response.json();if(!response.ok)throw Error(r.error||"Request failed");render(r);
    if (fresh || extra.action === "next") {
      $("starting").value = "";
      $("upcard").value = "random";
    }
    $("card").value="";
  } catch(e) {$("error").textContent=e.message;$("error").hidden=false;}
  finally {busy=false;controls();}
}
function starting() {return {cards:$("starting").value,upcard:$("upcard").value,threshold:$("threshold").value==="round" ? null : Number($("threshold").value)};}
function deal() {send(state ? {action:"next",...starting()} : starting(), !state);}
$("start-form").addEventListener("submit",e=>{e.preventDefault();if (!state || state.status === "settled") deal();});
$("new-shoe").addEventListener("click",()=>send(starting(),true));
$("method").addEventListener("change",()=>{if(state) send();});
$("threshold").addEventListener("change",()=>{if(state) send({action:"settings",threshold:starting().threshold});});
document.querySelectorAll("[data-action]").forEach(n=>n.addEventListener("click",()=>send({action:n.dataset.action})));
$("random-card").addEventListener("click",()=>send({action:"card",card:"random"}));
$("draw-form").addEventListener("submit",e=>{e.preventDefault();send({action:"card",card:$("card").value});});
$("next").addEventListener("click",deal);
$("suggestion").textContent = "Ready to deal";
$("hint").textContent = "Choose starting cards or leave them blank, then click Deal round.";
controls();
