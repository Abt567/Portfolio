document.addEventListener("DOMContentLoaded", function () {
  const tempInput = document.getElementById("temp_type");
  const btnC = document.getElementById("btn-c");
  const btnF = document.getElementById("btn-f");

  // If this page doesn't have the toggle, bail quietly.
  if (!tempInput || !btnC || !btnF) {
    return;
  }

  function setUnit(unit) {
    tempInput.value = unit;

    if (unit === "c") {
      btnC.classList.add("active");
      btnF.classList.remove("active");
      btnC.setAttribute("aria-pressed", "true");
      btnF.setAttribute("aria-pressed", "false");
    } else {
      btnF.classList.add("active");
      btnC.classList.remove("active");
      btnF.setAttribute("aria-pressed", "true");
      btnC.setAttribute("aria-pressed", "false");
    }
  }

  btnC.addEventListener("click", function () {
    setUnit("c");
  });

  btnF.addEventListener("click", function () {
    setUnit("f");
  });
});

