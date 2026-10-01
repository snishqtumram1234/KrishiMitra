"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { checkImage, type ImageCheck } from "@/lib/checks/validate";

export type PhotoState = {
  file: File;
  previewUrl: string;
  /** null while the file's first bytes are being read */
  check: ImageCheck | null;
};

/** One chosen photo: its preview URL (released when replaced or unmounted) and the result of the client-side checks. */
export function usePhoto() {
  const [photo, setPhoto] = useState<PhotoState | null>(null);
  const urlRef = useRef<string | null>(null);
  const latest = useRef(0);

  const release = () => {
    if (urlRef.current) URL.revokeObjectURL(urlRef.current);
    urlRef.current = null;
  };
  useEffect(() => release, []);

  const choose = useCallback(async (file: File) => {
    const id = ++latest.current;
    release();
    const previewUrl = URL.createObjectURL(file);
    urlRef.current = previewUrl;
    setPhoto({ file, previewUrl, check: null });
    const check = await checkImage(file);
    if (id === latest.current) setPhoto({ file, previewUrl, check });
  }, []);

  const clear = useCallback(() => {
    latest.current++;
    release();
    setPhoto(null);
  }, []);

  return { photo, choose, clear };
}
