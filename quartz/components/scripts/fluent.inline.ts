// 1. Reveal Highlight Effect (Global Listener)
const handleMouseMove = (e: MouseEvent) => {
  const cards = document.querySelectorAll(
    ".center, .sidebar .explorer, .sidebar .recent-notes, .sidebar .toc, .sidebar .backlinks, .popover"
  ) as NodeListOf<HTMLElement>;
  
  for (const card of cards) {
    const rect = card.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    card.style.setProperty("--mouse-x", `${x}px`);
    card.style.setProperty("--mouse-y", `${y}px`);
  }
};

// Only add the document listener once
if (!window.hasOwnProperty("fluentMotionInit")) {
  document.addEventListener("mousemove", handleMouseMove);
  (window as any).fluentMotionInit = true;
}

const maxTilt = 4; // degrees

function setupFluentMotion() {
  // 2. Stagger Animations for List Items
  const listItems = document.querySelectorAll(
    ".explorer ul li, .recent-notes ul li, .toc ul li"
  ) as NodeListOf<HTMLElement>;
  
  listItems.forEach((li, index) => {
    // Limit max delay to avoid too long waits
    const delay = Math.min(index * 40, 600);
    li.classList.add("stagger-item");
    li.style.animationDelay = `${delay}ms`;
  });

  // 3. 3D Card Tilt Effect (Only for sidebars & popovers)
  const tiltCards = document.querySelectorAll(
    ".sidebar .explorer, .sidebar .recent-notes, .sidebar .toc, .sidebar .backlinks, .popover"
  ) as NodeListOf<HTMLElement>;

  for (const card of tiltCards) {
    if (card.dataset.fluentTiltInit) continue;
    card.dataset.fluentTiltInit = "true";

    card.addEventListener("mousemove", (e: MouseEvent) => {
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const centerX = rect.width / 2;
      const centerY = rect.height / 2;

      const tiltX = ((y - centerY) / centerY) * -maxTilt;
      const tiltY = ((x - centerX) / centerX) * maxTilt;

      card.style.transform = `perspective(1000px) rotateX(${tiltX}deg) rotateY(${tiltY}deg) scale3d(1.02, 1.02, 1.02)`;
      card.style.transition = "transform 0.1s ease";
    });

    card.addEventListener("mouseleave", () => {
      card.style.transform = `perspective(1000px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)`;
      card.style.transition = "transform 0.4s ease";
    });
  }
}

// --- 4. Mobile Tap-to-Focus Interaction ---
function setupMobileInteraction() {
  // Mobile click-to-expand has been explicitly disabled per user request.
  if (window.innerWidth <= 768) {
    return;
  }

  const cards = document.querySelectorAll(
    ".center, .sidebar .explorer, .sidebar .recent-notes, .sidebar .toc, .sidebar .backlinks, .popover"
  ) as NodeListOf<HTMLElement>;
  
  const page = document.querySelector(".page") as HTMLElement;
  if (!page) return;

  // We use 'click' instead of touch events because modern mobile browsers perfectly differentiate 
  // between a swipe/scroll and a true 'tap' (click), making this 100% reliable.
  for (const card of cards) {
    card.addEventListener("click", (e: Event) => {
      // Don't trigger if they clicked a link or button
      const target = e.target as HTMLElement;
      if (target.tagName.toLowerCase() === "a" || target.closest("a") || target.closest("button")) {
        return; 
      }

      const isAlreadyFocused = card.classList.contains("mobile-focused");
      
      // Remove focus from all cards first
      cards.forEach(c => c.classList.remove("mobile-focused"));

      if (isAlreadyFocused) {
        // Toggle off
        page.classList.remove("has-mobile-focus");
      } else {
        // Toggle on
        card.classList.add("mobile-focused");
        page.classList.add("has-mobile-focus");
      }
    });
  }

  // Clear focus when tapping outside any card
  document.addEventListener("click", (e: Event) => {
    const target = e.target as HTMLElement;
    if (!target.closest(".center") && !target.closest(".sidebar > *")) {
      cards.forEach(c => c.classList.remove("mobile-focused"));
      page.classList.remove("has-mobile-focus");
    }
  });
}

// --- 5. Dark Mode View Transition Hack ---
function setupDarkmodeTransition() {
  const btn = document.querySelector(".darkmode") as HTMLElement;
  if (!btn || btn.dataset.transitionInit) return;
  btn.dataset.transitionInit = "true";

  // Clone button to strip default Quartz listeners
  const clone = btn.cloneNode(true) as HTMLElement;
  btn.replaceWith(clone);

  clone.addEventListener("click", (e) => {
    const isDark = document.documentElement.getAttribute("saved-theme") === "dark";
    const newTheme = isDark ? "light" : "dark";

    const applyTheme = () => {
      document.documentElement.setAttribute("saved-theme", newTheme);
      localStorage.setItem("theme", newTheme);
      document.body.classList.remove("theme-dark", "theme-light");
      document.body.classList.add(`theme-${newTheme}`);
      document.dispatchEvent(new CustomEvent("themechange", { detail: { theme: newTheme } }));
    };

    if (!document.startViewTransition) {
      applyTheme();
      return;
    }

    const x = e.clientX;
    const y = e.clientY;
    const endRadius = Math.hypot(Math.max(x, window.innerWidth - x), Math.max(y, window.innerHeight - y));

    const transition = document.startViewTransition(() => applyTheme());
    // No explicit clip-path animation here, so it will fall back to a beautiful, soft cross-fade default!
  });
}

// Edge blur removed per user request

// --- 7. Image Long-Press Zoom & Tilt ---
function setupImageZoom() {
  const images = document.querySelectorAll("article img") as NodeListOf<HTMLImageElement>;
  
  // Create overlay if it doesn't exist
  let overlay = document.getElementById("zoom-overlay");
  if (!overlay) {
    overlay = document.createElement("div");
    overlay.id = "zoom-overlay";
    document.body.appendChild(overlay);
  }

  for (const img of images) {
    if (img.dataset.zoomInit) continue;
    img.dataset.zoomInit = "true";
    
    let isPressed = false;
    let clone: HTMLImageElement | null = null;

    const release = () => {
      if (!isPressed) return;
      isPressed = false;
      document.body.classList.remove("image-zoomed");
      
      if (clone) {
        // Animate clone back to original position
        const rect = img.getBoundingClientRect();
        clone.style.width = `${rect.width}px`;
        clone.style.height = `${rect.height}px`;
        clone.style.left = `${rect.left}px`;
        clone.style.top = `${rect.top}px`;
        // Interpolatable transform so it doesn't snap instantly!
        clone.style.transform = `perspective(1000px) rotateX(0deg) rotateY(0deg) scale(1)`;
        clone.style.boxShadow = `none`;
        
        const currentClone = clone;
        setTimeout(() => {
          if (currentClone.parentNode) currentClone.parentNode.removeChild(currentClone);
          img.style.visibility = "visible";
        }, 450); // Wait slightly longer than transition to ensure it finishes
        clone = null;
      }
    };

    // Handle mouse down to start zoom
    img.addEventListener("mousedown", (e: MouseEvent) => {
      if (e.button !== 0) return; // Only left click
      e.preventDefault(); // Prevent default drag
      isPressed = true;
      document.body.classList.add("image-zoomed");
      
      // 1. Get original position
      const rect = img.getBoundingClientRect();
      
      // 2. Create a clone appended to body to escape stacking contexts
      clone = document.createElement("img");
      clone.src = img.src;
      clone.style.position = "fixed";
      clone.style.zIndex = "9999999";
      clone.style.pointerEvents = "none";
      clone.style.transition = "all 0.4s cubic-bezier(0.2, 0.8, 0.2, 1)";
      clone.style.transformOrigin = "center center";
      clone.style.boxShadow = "0 12px 36px rgba(0, 0, 0, 0.2)";
      clone.style.margin = "0";
      clone.style.padding = "0";
      
      const computedStyle = window.getComputedStyle(img);
      clone.style.objectFit = computedStyle.objectFit !== 'fill' ? computedStyle.objectFit : 'contain';
      clone.style.borderRadius = computedStyle.borderRadius;
      
      // Start exactly at original position
      clone.style.top = `${rect.top}px`;
      clone.style.left = `${rect.left}px`;
      clone.style.width = `${rect.width}px`;
      clone.style.height = `${rect.height}px`;
      
      // explicitly clear transform to prevent mismatch
      clone.style.transform = `none`; 
      
      document.body.appendChild(clone);
      img.style.visibility = "hidden";
      
      // 3. Calculate target enlarged dimensions (max 80% viewport)
      const aspect = img.naturalWidth / img.naturalHeight;
      let targetW = window.innerWidth * 0.8;
      let targetH = targetW / aspect;
      if (targetH > window.innerHeight * 0.8) {
        targetH = window.innerHeight * 0.8;
        targetW = targetH * aspect;
      }
      
      // Force layout calculation so the browser applies the start state
      clone.getBoundingClientRect();
      
      // 4. Animate to center and enlarged size
      clone.style.width = `${targetW}px`;
      clone.style.height = `${targetH}px`;
      clone.style.left = `${(window.innerWidth - targetW) / 2}px`;
      clone.style.top = `${(window.innerHeight - targetH) / 2}px`;
      clone.style.boxShadow = "0 40px 100px rgba(0, 0, 0, 0.6)";

      applyTilt(e);
    });

    const applyTilt = (e: MouseEvent) => {
      if (!clone) return;
      const centerX = window.innerWidth / 2;
      const centerY = window.innerHeight / 2;
      const tiltX = ((e.clientY - centerY) / centerY) * -8;
      const tiltY = ((e.clientX - centerX) / centerX) * 8;
      clone.style.transform = `perspective(1000px) rotateX(${tiltX}deg) rotateY(${tiltY}deg)`;
    };

    window.addEventListener("mousemove", (e: MouseEvent) => {
      if (!isPressed) return;
      applyTilt(e);
    });

    window.addEventListener("mouseup", release);
    window.addEventListener("scroll", release, { passive: true });
  }
}

// --- 8. Dynamic Custom Cursor ---
function setupCustomCursor() {
  if (!window.matchMedia("(pointer: fine)").matches) return; // Only on desktop
  
  let cursor = document.getElementById("fluent-cursor");
  if (!cursor) {
    cursor = document.createElement("div");
    cursor.id = "fluent-cursor";
    document.body.appendChild(cursor);
  }
  document.documentElement.classList.add("custom-cursor-active");

  let mouseX = (window as any).lastMouseX || window.innerWidth / 2;
  let mouseY = (window as any).lastMouseY || window.innerHeight / 2;
  
  // Set initial position immediately to prevent top-left flash
  cursor.style.transform = `perspective(600px) translate3d(${mouseX}px, ${mouseY}px, 0) rotateZ(15deg) rotateX(0deg) rotateY(0deg) scale(1)`;

  // Clean up old listeners to support SPA navigation and Hot-Reloading
  if ((window as any).fluentCursorCleanup) {
    (window as any).fluentCursorCleanup();
  }

  let cursorX = mouseX;
  let cursorY = mouseY;
  let currentTiltX = 0;
  let currentTiltY = 0;
  let currentScale = 1;
  let isMoving = false;
  let isPressing = false;
  let rafId = 0;

  const onMouseMove = (e: MouseEvent) => {
    mouseX = e.clientX;
    mouseY = e.clientY;
    (window as any).lastMouseX = mouseX;
    (window as any).lastMouseY = mouseY;
    if (!isMoving) {
      isMoving = true;
      rafId = requestAnimationFrame(render);
    }
  };
  
  const onMouseDown = () => {
    isPressing = true;
    if (!isMoving) { isMoving = true; rafId = requestAnimationFrame(render); }
  };
  
  const onMouseUp = () => {
    isPressing = false;
    if (!isMoving) { isMoving = true; rafId = requestAnimationFrame(render); }
  };
  
  const onMouseOver = (e: MouseEvent) => {
    const target = e.target as HTMLElement;
    const isInteractable = target.closest("a, button, input, textarea, .card, article img");
    const activeCursor = document.getElementById("fluent-cursor");
    if (activeCursor) {
      if (isInteractable) {
        activeCursor.classList.add("hovering");
      } else {
        activeCursor.classList.remove("hovering");
      }
    }
  };

  window.addEventListener("mousemove", onMouseMove);
  window.addEventListener("mousedown", onMouseDown);
  window.addEventListener("mouseup", onMouseUp);
  window.addEventListener("mouseover", onMouseOver);

  (window as any).fluentCursorCleanup = () => {
    window.removeEventListener("mousemove", onMouseMove);
    window.removeEventListener("mousedown", onMouseDown);
    window.removeEventListener("mouseup", onMouseUp);
    window.removeEventListener("mouseover", onMouseOver);
    cancelAnimationFrame(rafId);
  };

  const render = () => {
    // High lerp factor (0.6) for position keeps latency very low
    const lerp = 0.6; 
    const dx = mouseX - cursorX;
    const dy = mouseY - cursorY;
    
    cursorX += dx * lerp;
    cursorY += dy * lerp;

    // Use instantaneous dx/dy to calculate target tilt.
    // We use a small divisor (20) so even normal mouse movements create a strong target tilt.
    const maxTilt = 45;
    let targetTiltX = (dy / 20) * -maxTilt;
    let targetTiltY = (dx / 20) * maxTilt;
    
    // Clamp target tilt
    targetTiltX = Math.max(-maxTilt, Math.min(maxTilt, targetTiltX));
    targetTiltY = Math.max(-maxTilt, Math.min(maxTilt, targetTiltY));

    // THE SECRET SAUCE: Independently smooth the tilt with a low lerp (0.15)
    // This allows the cursor position to instantly track the mouse, 
    // but the 3D tilt "hangs" and acts like a physical spring!
    currentTiltX += (targetTiltX - currentTiltX) * 0.15;
    currentTiltY += (targetTiltY - currentTiltY) * 0.15;

    // Scale calculation (squish when moving fast, or clicking)
    const speed = Math.min(Math.sqrt(dx * dx + dy * dy), 30);
    let targetScale = 1 - (speed / 30) * 0.15;
    if (isPressing) targetScale *= 0.8;
    
    currentScale += (targetScale - currentScale) * 0.2;

    const activeCursor = document.getElementById("fluent-cursor");
    if (activeCursor) {
      activeCursor.style.transform = `perspective(600px) translate3d(${cursorX}px, ${cursorY}px, 0) rotateZ(15deg) rotateX(${currentTiltX}deg) rotateY(${currentTiltY}deg) scale(${currentScale})`;
    }

    // Stop animation loop if everything has settled
    if (Math.abs(dx) < 0.1 && Math.abs(dy) < 0.1 && Math.abs(currentTiltX) < 0.1 && Math.abs(currentTiltY) < 0.1 && Math.abs(currentScale - (isPressing ? 0.8 : 1)) < 0.01) {
      isMoving = false;
      if (activeCursor) {
        activeCursor.style.transform = `perspective(600px) translate3d(${mouseX}px, ${mouseY}px, 0) rotateZ(15deg) rotateX(0deg) rotateY(0deg) scale(${isPressing ? 0.8 : 1})`;
      }
    } else {
      rafId = requestAnimationFrame(render);
    }
  };
}

document.addEventListener("nav", () => {
  setupFluentMotion();
  setupMobileInteraction();
  setupDarkmodeTransition();
  setupImageZoom();
  setupCustomCursor();
});
window.addEventListener("DOMContentLoaded", () => {
  setupFluentMotion();
  setupMobileInteraction();
  setupDarkmodeTransition();
  setupImageZoom();
  setupCustomCursor();
});
// Run once immediately in case DOM is already loaded
setupFluentMotion();
setupMobileInteraction();
setupDarkmodeTransition();
setupImageZoom();
setupCustomCursor();

