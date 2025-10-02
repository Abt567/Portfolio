// Runs after HTML parsed because we used `defer`
(function () {
  const btnC = document.getElementById('btn-c');
  const btnF = document.getElementById('btn-f');
  const hidden = document.getElementById('temp_type');

  function setTempType(t) {
    hidden.value = t;
    const cActive = t === 'c';
    btnC.classList.toggle('active', cActive);
    btnF.classList.toggle('active', !cActive);
    btnC.setAttribute('aria-pressed', String(cActive));
    btnF.setAttribute('aria-pressed', String(!cActive));
  }

  if (btnC && btnF && hidden) {
    btnC.addEventListener('click', () => setTempType('c'));
    btnF.addEventListener('click', () => setTempType('f'));
    // default
    setTempType('c');
  }
})();
