document.addEventListener("DOMContentLoaded", () => {
  const hint = document.getElementById("orientationHint");
  const closeBtn = hint ? hint.querySelector(".orientation-hint__close") : null;

  const DISMISS_KEY = "orientationHintDismissed";
  const mq = (q) => (window.matchMedia ? window.matchMedia(q).matches : false);

  // ✅ NEW: keep a real viewport-height variable in sync (Safari bars issue)
  const syncViewportVars = () => {
    const vv = window.visualViewport;

    // vv.height is the usable area (changes when Safari bars show/hide)
    const h = vv ? vv.height : window.innerHeight;
    const w = vv ? vv.width : window.innerWidth;

    document.documentElement.style.setProperty("--vvh", `${h}px`);
    document.documentElement.style.setProperty("--vvw", `${w}px`);
  };

  const isPhoneLike = () => {
    const vvW = window.visualViewport ? window.visualViewport.width : window.innerWidth;
    return mq("(pointer: coarse)") || mq("(hover: none)") || vvW <= 900;
  };

  const syncHint = () => {
    const w = window.visualViewport ? window.visualViewport.width : window.innerWidth;
    const h = window.visualViewport ? window.visualViewport.height : window.innerHeight;

    // Some browsers lie about (orientation). This doesn't.
    const isLandscape = w > h;
    const phoneLike = isPhoneLike();

    // CSS hook for your landscape fixes
    document.body.classList.toggle("phone-landscape", Boolean(phoneLike && isLandscape));

    // Show hint only on phone-like portrait, unless dismissed
    if (hint) {
      const dismissed = localStorage.getItem(DISMISS_KEY) === "1";
      const shouldShow = phoneLike && !isLandscape && !dismissed;

      hint.hidden = !shouldShow;
      hint.setAttribute("aria-hidden", shouldShow ? "false" : "true");
    }
  };

  // Initial
  syncViewportVars();
  syncHint();

  // Update on viewport/orientation changes
  window.addEventListener("resize", () => {
    syncViewportVars();
    syncHint();
  }, { passive: true });

  window.addEventListener("orientationchange", () => {
    syncViewportVars();
    syncHint();
  }, { passive: true });

  // iOS: visualViewport changes when the browser bars hide/show.
  if (window.visualViewport) {
    window.visualViewport.addEventListener("resize", () => {
      syncViewportVars();
      syncHint();
    }, { passive: true });

    window.visualViewport.addEventListener("scroll", () => {
      syncViewportVars();
      syncHint();
    }, { passive: true });
  }

  // Dismiss
  if (closeBtn && hint) {
    closeBtn.addEventListener("click", () => {
      localStorage.setItem(DISMISS_KEY, "1");
      hint.hidden = true;
      hint.setAttribute("aria-hidden", "true");
    });
  }

  // --- your existing forecast-box active state ---
  const boxes = document.querySelectorAll(".forecast-box");
  boxes.forEach((b) => {
    b.addEventListener("click", () => {
      boxes.forEach((x) => x.classList.remove("active"));
      b.classList.add("active");
    });

    b.addEventListener("blur", () => b.classList.remove("active"));

    b.addEventListener("keypress", (e) => {
      if (e.key === "Enter" || e.key === " ") b.click();
    });
  });
});

  // ===============================
  // iOS Safari fix: lock hourly strip to horizontal-only
  // (prevents vertical rubber-band / drift on older iPhones)
  // ===============================
  const scroller = document.querySelector(".forecast_container");

  if (scroller) {
    let startX = 0;
    let startY = 0;
    let locked = false; // once we decide direction, stick to it

    scroller.addEventListener(
      "touchstart",
      (e) => {
        if (!e.touches || e.touches.length !== 1) return;
        const t = e.touches[0];
        startX = t.clientX;
        startY = t.clientY;
        locked = false;
      },
      { passive: true }
    );

    scroller.addEventListener(
      "touchmove",
      (e) => {
        if (!e.touches || e.touches.length !== 1) return;

        const t = e.touches[0];
        const dx = Math.abs(t.clientX - startX);
        const dy = Math.abs(t.clientY - startY);

        // Decide direction once (small deadzone prevents jitter)
        if (!locked && dx + dy > 10) locked = true;

        // If it's mostly vertical, block it hard.
        // This stops the iPhone 12 “up/down drift” inside the horizontal strip.
        if (dy > dx) {
          e.preventDefault();
        }
      },
      { passive: false } // must be false or preventDefault does nothing
    );
  }

