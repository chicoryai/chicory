/**
 * Animation configurations and utilities for panel transitions
 */

import { Variants } from "framer-motion";

// Animation timing constants
export const ANIMATION_DURATION = {
  instant: 0,
  fast: 0.15,
  normal: 0.3,
  slow: 0.5,
  deliberate: 0.7,
} as const;

// Easing functions
export const ANIMATION_EASING = {
  smooth: [0.4, 0, 0.2, 1],
  bounce: [0.68, -0.55, 0.265, 1.55],
  sharp: [0.4, 0, 0.6, 1],
  elastic: [0.68, -0.6, 0.32, 1.6],
} as const;

// Sidebar animation variants
export const sidebarVariants: Variants = {
  closed: {
    x: "100%",
    opacity: 0,
    transition: {
      duration: ANIMATION_DURATION.fast,
      ease: ANIMATION_EASING.sharp,
    },
  },
  open: {
    x: 0,
    opacity: 1,
    transition: {
      duration: ANIMATION_DURATION.normal,
      ease: ANIMATION_EASING.smooth,
    },
  },
};

// Backdrop animation variants
export const backdropVariants: Variants = {
  hidden: {
    opacity: 0,
    transition: {
      duration: ANIMATION_DURATION.fast,
    },
  },
  visible: {
    opacity: 1,
    transition: {
      duration: ANIMATION_DURATION.fast,
    },
  },
};

// Tab content animation variants
export const tabContentVariants: Variants = {
  inactive: {
    opacity: 0,
    y: 8,
    transition: {
      duration: ANIMATION_DURATION.fast,
      ease: ANIMATION_EASING.smooth,
    },
  },
  active: {
    opacity: 1,
    y: 0,
    transition: {
      duration: ANIMATION_DURATION.fast,
      ease: ANIMATION_EASING.smooth,
    },
  },
};

// Collapsible section variants
export const collapsibleVariants: Variants = {
  collapsed: {
    height: 0,
    opacity: 0,
    transition: {
      height: {
        duration: ANIMATION_DURATION.normal,
        ease: ANIMATION_EASING.smooth,
      },
      opacity: {
        duration: ANIMATION_DURATION.fast,
        ease: "linear",
      },
    },
  },
  expanded: {
    height: "auto",
    opacity: 1,
    transition: {
      height: {
        duration: ANIMATION_DURATION.normal,
        ease: ANIMATION_EASING.smooth,
      },
      opacity: {
        duration: ANIMATION_DURATION.fast,
        ease: "linear",
        delay: 0.1,
      },
    },
  },
};

// List stagger animation variants
export const listContainerVariants: Variants = {
  hidden: {
    opacity: 0,
  },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.05,
      delayChildren: 0.1,
    },
  },
};

export const listItemVariants: Variants = {
  hidden: {
    opacity: 0,
    y: 20,
  },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: ANIMATION_DURATION.normal,
      ease: ANIMATION_EASING.smooth,
    },
  },
};

// Button interaction variants
export const buttonVariants: Variants = {
  idle: {
    scale: 1,
    y: 0,
  },
  hover: {
    scale: 1.02,
    y: -2,
    transition: {
      duration: ANIMATION_DURATION.fast,
      ease: ANIMATION_EASING.smooth,
    },
  },
  tap: {
    scale: 0.98,
    y: 0,
    transition: {
      duration: 0.05,
      ease: ANIMATION_EASING.sharp,
    },
  },
};

// Progress bar variants
export const progressBarVariants: Variants = {
  initial: {
    scaleX: 0,
    originX: 0,
  },
  animate: (progress: number) => ({
    scaleX: progress / 100,
    transition: {
      duration: ANIMATION_DURATION.slow,
      ease: ANIMATION_EASING.smooth,
    },
  }),
};

// Success checkmark variants
export const checkmarkVariants: Variants = {
  hidden: {
    pathLength: 0,
    opacity: 0,
  },
  visible: {
    pathLength: 1,
    opacity: 1,
    transition: {
      pathLength: {
        duration: ANIMATION_DURATION.normal,
        ease: ANIMATION_EASING.smooth,
      },
      opacity: {
        duration: ANIMATION_DURATION.fast,
      },
    },
  },
};

// Error shake animation
export const shakeVariants: Variants = {
  initial: {
    x: 0,
  },
  shake: {
    x: [0, -8, 8, -8, 8, 0],
    transition: {
      duration: ANIMATION_DURATION.normal,
      ease: ANIMATION_EASING.sharp,
    },
  },
};

// Pulse animation for saving state
export const pulseVariants: Variants = {
  initial: {
    scale: 1,
    opacity: 1,
  },
  pulse: {
    scale: [1, 1.05, 1],
    opacity: [1, 0.8, 1],
    transition: {
      duration: ANIMATION_DURATION.deliberate,
      ease: ANIMATION_EASING.smooth,
      repeat: Infinity,
    },
  },
};

// Utility function to check for reduced motion preference
export const shouldReduceMotion = (): boolean => {
  if (typeof window === "undefined") return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
};

// Utility to get animation duration based on preference
export const getAnimationDuration = (duration: keyof typeof ANIMATION_DURATION): number => {
  if (shouldReduceMotion()) return 0.01;
  return ANIMATION_DURATION[duration];
};

// Utility to create custom spring animation
export const springAnimation = (stiffness = 300, damping = 30) => ({
  type: "spring",
  stiffness,
  damping,
});

// Utility for scroll-triggered animations
export const scrollTriggerVariants: Variants = {
  offscreen: {
    y: 50,
    opacity: 0,
  },
  onscreen: {
    y: 0,
    opacity: 1,
    transition: {
      duration: ANIMATION_DURATION.normal,
      ease: ANIMATION_EASING.smooth,
    },
  },
};

// Content block fade-in variants (for tool use, thinking blocks)
export const contentBlockVariants: Variants = {
  hidden: {
    opacity: 0,
    y: 8,
  },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: ANIMATION_DURATION.normal,
      ease: ANIMATION_EASING.smooth,
    },
  },
};

// Simple ease-in for initial render (no dramatic reveal)
export const easeInVariants: Variants = {
  hidden: {
    opacity: 0,
  },
  visible: {
    opacity: 1,
    transition: {
      duration: ANIMATION_DURATION.fast,
      ease: ANIMATION_EASING.smooth,
    },
  },
};

// Scroll roll reveal variants (unrolling from top like a scroll)
export const textRevealVariants: Variants = {
  hidden: {
    scaleY: 0,
    opacity: 0,
    transformOrigin: "top",
  },
  visible: {
    scaleY: 1,
    opacity: 1,
    transformOrigin: "top",
    transition: {
      scaleY: {
        duration: ANIMATION_DURATION.deliberate * 2,
        ease: ANIMATION_EASING.smooth,
      },
      opacity: {
        duration: ANIMATION_DURATION.normal,
        ease: "linear",
      },
    },
  },
};

// Blur overlay that fades out as text reveal completes
export const textRevealBlurVariants: Variants = {
  visible: {
    opacity: 1,
  },
  hidden: {
    opacity: 0,
    transition: {
      duration: ANIMATION_DURATION.deliberate,
      delay: ANIMATION_DURATION.deliberate * 1.5,
      ease: ANIMATION_EASING.smooth,
    },
  },
};