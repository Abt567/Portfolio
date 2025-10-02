// Runs after HTML parsed because we used `defer`
(function () {
  const boxes = document.querySelectorAll('.forecast-box');
  if (!boxes.length) return;

  boxes.forEach(b => {
    b.addEventListener('click', () => {
      boxes.forEach(x => x.classList.remove('active'));
      b.classList.add('active');
    });
    b.addEventListener('blur', () => b.classList.remove('active'));
    b.addEventListener('keypress', (e) => {
      if (e.key === 'Enter' || e.key === ' ') { b.click(); }
    });
  });
})();
