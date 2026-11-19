"use client";

import { MessageCircle } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useState } from "react";

import { useI18n } from "@/i18n/client";

/** Floating shortcut to the assistant, shown once the hero has scrolled away. */
export function AssistantButton() {
  const { t } = useI18n();
  const [show, setShow] = useState(false);
  useEffect(() => {
    const onScroll = () => {
      const target = document.getElementById("assistant")?.getBoundingClientRect();
      setShow(window.scrollY > 600 && !(target && target.top < window.innerHeight && target.bottom > 0));
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);
  return (
    <AnimatePresence>
      {show && (
        <motion.a href="#assistant" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 16 }}
          onClick={() => setTimeout(() => document.getElementById("assistant-input")?.focus(), 450)}
          className="fixed bottom-[calc(1.25rem+env(safe-area-inset-bottom,0px))] right-[calc(1.25rem+env(safe-area-inset-right,0px))] z-30 inline-flex min-h-12 items-center gap-2 rounded-full bg-accent px-5 font-semibold text-navy shadow-xl shadow-navy/25">
          <MessageCircle aria-hidden="true" size={18} /> {t.assistant.button}
        </motion.a>
      )}
    </AnimatePresence>
  );
}
