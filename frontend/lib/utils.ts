import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function commaJoin(values: string[]) {
  return values.filter(Boolean).join("、");
}

export function splitComma(input: string) {
  return input
    .split(/[,\n，]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

