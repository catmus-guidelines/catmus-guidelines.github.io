/* Interface behaviour for the new theme: the mobile navigation drawer and the
   light/dark switch. Loaded only when the site is built with --theme=new. */

(function () {
   /* ---- light / dark -------------------------------------------------- */
   const STORAGE_KEY = 'catmus_theme';
   const root = document.documentElement;

   let stored = null;
   try {
      stored = localStorage.getItem(STORAGE_KEY);
   } catch (error) {
      stored = null; // private browsing, or storage disabled
   }
   if (stored === 'light' || stored === 'dark') {
      root.setAttribute('data-theme', stored);
   }

   const toggle = document.querySelector('.theme-toggle');
   if (toggle) {
      toggle.addEventListener('click', function () {
         // With no explicit choice yet, flip away from whatever the OS asked for.
         const current =
            root.getAttribute('data-theme') ||
            (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
         const next = current === 'dark' ? 'light' : 'dark';
         root.setAttribute('data-theme', next);
         try {
            localStorage.setItem(STORAGE_KEY, next);
         } catch (error) {
            /* not persisting is survivable */
         }
      });
   }

   /* ---- mobile drawer -------------------------------------------------- */
   const navToggle = document.querySelector('.nav-toggle');
   const sidebar = document.getElementById('sidebar');
   if (!navToggle || !sidebar) {
      return;
   }

   function setOpen(open) {
      document.body.classList.toggle('nav-open', open);
      navToggle.setAttribute('aria-expanded', String(open));
   }

   navToggle.addEventListener('click', function (event) {
      event.stopPropagation();
      setOpen(!document.body.classList.contains('nav-open'));
   });

   // Tapping a link, tapping outside, or Escape all close the drawer; without
   // this it stays open over the page it just navigated to.
   sidebar.addEventListener('click', function (event) {
      if (event.target.closest('a')) {
         setOpen(false);
      }
   });

   document.addEventListener('click', function (event) {
      if (
         document.body.classList.contains('nav-open') &&
         !sidebar.contains(event.target) &&
         !navToggle.contains(event.target)
      ) {
         setOpen(false);
      }
   });

   document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') {
         setOpen(false);
      }
   });
})();
