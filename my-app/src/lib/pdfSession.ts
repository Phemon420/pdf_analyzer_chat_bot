export function savePdfToSession(file: File) {
  const reader = new FileReader();
  reader.onload = () => {
    sessionStorage.setItem('activePdf', reader.result as string);
  };
  reader.readAsDataURL(file);
}

export function loadPdfFromSession(): string | null {
  return sessionStorage.getItem('activePdf');
}

export function clearPdfSession() {
  sessionStorage.removeItem('activePdf');
}
