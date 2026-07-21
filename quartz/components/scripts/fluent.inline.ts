document.addEventListener("nav", () => {
  // 1. Reveal Highlight Effect
  const cards = document.querySelectorAll(
    ".center, .sidebar .explorer, .sidebar .recent-notes, .sidebar .toc, .sidebar .backlinks, .popover"
  ) as NodeListOf<HTMLElement>;

  const handleMouseMove = (e: MouseEvent) => {
    for (const card of cards) {
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      card.style.setProperty("--mouse-x", `${x}px`);
      card.style.setProperty("--mouse-y", `${y}px`);
    }
  };

  document.addEventListener("mousemove", handleMouseMove);

  // 2. 3D Card Tilt Effect (Only for sidebars & popovers)
  const maxTilt = 4; // degrees
  for (const card of cards) {
    if (card.classList.contains("center")) continue; // Skip main content

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

  // 3. Stagger Animations for List Items
  const listItems = document.querySelectorAll(
    ".explorer ul li, .recent-notes ul li, .toc ul li"
  ) as NodeListOf<HTMLElement>;
  
  listItems.forEach((li, index) => {
    // Limit max delay to avoid too long waits
    const delay = Math.min(index * 40, 600);
    li.classList.add("stagger-item");
    li.style.animationDelay = `${delay}ms`;
  });

  // Clean up global listener on SPA navigation
  window.addCleanup(() => {
    document.removeEventListener("mousemove", handleMouseMove);
  });
});
