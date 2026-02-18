const TOTAL_NUMBERS = 90;
const POOL = Array.from({ length: TOTAL_NUMBERS }, (_, index) => index + 1);

const currentNumber = document.getElementById('currentNumber');
const count = document.getElementById('count');
const remaining = document.getElementById('remaining');
const history = document.getElementById('history');
const board = document.getElementById('board');
const nextBtn = document.getElementById('nextBtn');
const autoBtn = document.getElementById('autoBtn');
const resetBtn = document.getElementById('resetBtn');

let available = [...POOL];
let called = [];
let autoTimer = null;

function renderBoard() {
  board.innerHTML = '';
  POOL.forEach((number) => {
    const cell = document.createElement('div');
    cell.className = `cell${called.includes(number) ? ' called' : ''}`;
    cell.textContent = number;
    board.appendChild(cell);
  });
}

function refreshStatus() {
  const lastCalled = called.at(-1);
  currentNumber.textContent = lastCalled ?? '--';
  count.textContent = `${called.length} / ${TOTAL_NUMBERS}`;
  remaining.textContent = String(TOTAL_NUMBERS - called.length);

  history.innerHTML = '';
  called
    .slice(-12)
    .reverse()
    .forEach((number) => {
      const li = document.createElement('li');
      li.textContent = number;
      history.appendChild(li);
    });

  nextBtn.disabled = called.length === TOTAL_NUMBERS;

  if (called.length === TOTAL_NUMBERS && autoTimer) {
    toggleAutoCall();
  }

  renderBoard();
}

function callNextNumber() {
  if (!available.length) {
    return;
  }

  const index = Math.floor(Math.random() * available.length);
  const [picked] = available.splice(index, 1);
  called.push(picked);
  refreshStatus();
}

function toggleAutoCall() {
  if (autoTimer) {
    clearInterval(autoTimer);
    autoTimer = null;
    autoBtn.textContent = 'Start Auto Call';
    return;
  }

  autoTimer = setInterval(callNextNumber, 2000);
  autoBtn.textContent = 'Stop Auto Call';
}

function resetGame() {
  available = [...POOL];
  called = [];

  if (autoTimer) {
    clearInterval(autoTimer);
    autoTimer = null;
    autoBtn.textContent = 'Start Auto Call';
  }

  refreshStatus();
}

nextBtn.addEventListener('click', callNextNumber);
autoBtn.addEventListener('click', toggleAutoCall);
resetBtn.addEventListener('click', resetGame);

refreshStatus();
