import { create } from "zustand";

type UiState = {
  sourceId: string;
  setSourceId: (sourceId: string) => void;
};

export const useUiStore = create<UiState>((set) => ({
  sourceId: "",
  setSourceId: (sourceId) => set({ sourceId }),
}));

