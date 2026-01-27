'use client';

import dynamic from 'next/dynamic';
import { motion, AnimatePresence } from 'framer-motion';

const PDFViewerClient = dynamic(
  () => import('./pdfviewerclient'),
  { ssr: false }
);

interface PDFViewerProps {
  fileUrl: string;
  activePage?: number;
  isOpen: boolean;
  onClose: () => void;
}

// export default function PDFViewer({ fileUrl, activePage, onClose }: PDFViewerProps) {
//   if (!fileUrl) return null;

//   return (
//     <div className="fixed inset-0 z-100 flex items-center justify-center p-4 md:p-10">
//       {/* Backdrop: Clicking this closes the viewer */}
//       <div 
//         className="absolute inset-0 bg-black/60 backdrop-blur-sm" 
//         onClick={onClose}
//       />

//       {/* PDF Container */}
//       <div className="relative w-full max-w-5xl h-full bg-white dark:bg-gray-900 rounded-xl shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-200">
//         {/* Close Button Header */}
//         <div className="absolute top-4 right-4 z-110">
//           <button 
//             onClick={onClose}
//             className="p-2 bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 rounded-full transition-colors"
//           >
//             <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
//           </button>
//         </div>

//         <PDFViewerClient fileUrl={fileUrl} activePage={activePage} />
//       </div>
//     </div>
//   );
// }



export default function PDFViewer({ fileUrl, activePage, isOpen, onClose }: PDFViewerProps) {
  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-y-0 right-0 z-[100] flex items-center justify-end p-0 md:p-0 w-full max-w-2xl pointer-events-none">
          {/* Backdrop: REMOVED backdrop-blur to allow seeing chat behind/beside it */}
          {/* We keep a very subtle overlay or just the panel */}

          {/* PDF Panel: Slides from right */}
          <motion.div
            initial={{ x: '100%', opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: '100%', opacity: 0 }}
            transition={{ type: 'spring', damping: 25, stiffness: 200, duration: 0.4 }}
            className="relative w-full h-full bg-white dark:bg-gray-900 shadow-[-10px_0_30px_rgba(0,0,0,0.1)] overflow-hidden pointer-events-auto border-l border-gray-200 dark:border-gray-800"
          >
            {/* Close Button */}
            <button
              onClick={onClose}
              className="absolute top-4 right-4 z-[110] p-2 bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 rounded-full shadow-sm transition-colors"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
            </button>

            <PDFViewerClient fileUrl={fileUrl} activePage={activePage} />
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}