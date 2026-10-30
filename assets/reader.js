(()=>{'use strict';
const words=JSON.parse(document.getElementById('glossary-data').textContent);
const popup=document.getElementById('word-popup');let active=null;let suppressFocus=false;
function closeWord(){popup.hidden=true;if(active)active.setAttribute('aria-expanded','false');}
function showWord(btn){if(!document.getElementById('annotations-toggle').checked)return;const w=words[Number(btn.dataset.word)];if(!w)return;if(active&&active!==btn)active.setAttribute('aria-expanded','false');active=btn;btn.setAttribute('aria-expanded','true');document.getElementById('word-title').textContent=btn.textContent;document.getElementById('word-meaning').textContent=w.meaning;document.getElementById('word-detail').textContent=w.detail;popup.hidden=false;}
document.addEventListener('click',e=>{const btn=e.target.closest('button.vocab');if(btn){showWord(btn);return;}if(e.target.closest('.popup-close')){closeWord();suppressFocus=true;active?.focus();suppressFocus=false;return;}if(!e.target.closest('.word-popup'))closeWord();});
document.addEventListener('focusin',e=>{if(!suppressFocus&&e.target.matches('button.vocab:focus-visible'))showWord(e.target);});
document.addEventListener('keydown',e=>{if(e.key==='Escape'){closeWord();const g=document.getElementById('glossary-dialog');if(g.open){e.preventDefault();g.close();}}});
document.getElementById('reading-mode').addEventListener('change',e=>{document.body.classList.remove('mode-en','mode-zh');if(e.target.value!=='bilingual')document.body.classList.add('mode-'+e.target.value);closeWord();});
document.getElementById('annotations-toggle').addEventListener('change',e=>{document.body.classList.toggle('no-annotations',!e.target.checked);document.querySelectorAll('.vocab').forEach(b=>b.tabIndex=e.target.checked?0:-1);closeWord();});
const dialog=document.getElementById('glossary-dialog');const search=document.getElementById('word-search');
function fillList(){const q=search.value.trim().toLowerCase();const filtered=words.filter(w=>[...w.forms,w.meaning,w.detail].join(' ').toLowerCase().includes(q));const list=document.getElementById('word-list');list.replaceChildren();for(const w of filtered){const li=document.createElement('li');const term=document.createElement('span');term.className='gloss-term';term.textContent=w.term;const meaning=document.createElement('span');meaning.className='gloss-meaning';meaning.textContent=w.meaning;const detail=document.createElement('div');detail.className='gloss-detail';detail.textContent=w.detail;li.append(term,meaning,detail);list.append(li);}document.getElementById('word-count').textContent=filtered.length+' 个词条 / 共 '+words.length+' 个';}
document.getElementById('open-glossary').addEventListener('click',()=>{closeWord();fillList();dialog.showModal();search.focus();});
dialog.querySelector('.dialog-close').addEventListener('click',()=>dialog.close());
dialog.addEventListener('click',e=>{if(e.target===dialog){const r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)dialog.close();}});
search.addEventListener('input',fillList);
})();
