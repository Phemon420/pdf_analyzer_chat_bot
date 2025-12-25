// 'use client';

// import React, { useEffect } from 'react';
// import { Viewer, Worker } from '@react-pdf-viewer/core';
// import { defaultLayoutPlugin } from '@react-pdf-viewer/default-layout';

// // Import required styles
// import '@react-pdf-viewer/core/lib/styles/index.css';
// import '@react-pdf-viewer/default-layout/lib/styles/index.css';

// interface Props {
//   fileUrl: string;
//   activePage?: number;
// }

// export default function PDFViewerClient({ fileUrl, activePage }: Props) {
//   // 1. Create the plugin instance
//   const defaultLayoutPluginInstance = defaultLayoutPlugin();
  
//   // 2. Extract the jumpToPage function correctly from the store
//   const { jumpToPage } = defaultLayoutPluginInstance;

//   useEffect(() => {
//     if (activePage && activePage >= 1) {
//       // 3. Use a small timeout to ensure the viewer is ready to receive commands
//       const timer = setTimeout(() => {
//         if (typeof jumpToPage === 'function') {
//           jumpToPage(activePage - 1);
//         } else {
//            console.warn("PDF Viewer: jumpToPage is not yet available.");
//         }
//       }, 300); // 300ms is usually enough for the canvas to initialize

//       return () => clearTimeout(timer);
//     }
//   }, [activePage, jumpToPage]);

//   return (
//     <div className="h-full w-full">
//       <Worker workerUrl="https://unpkg.com/pdfjs-dist@3.11.174/build/pdf.worker.min.js">
//         <Viewer
//           fileUrl={fileUrl}
//           plugins={[defaultLayoutPluginInstance]}
//         />
//       </Worker>
//     </div>
//   );
// }










'use client';

import React, { useEffect } from 'react';
import { Viewer, Worker } from '@react-pdf-viewer/core';
import { defaultLayoutPlugin } from '@react-pdf-viewer/default-layout';
import { pageNavigationPlugin } from '@react-pdf-viewer/page-navigation';

import '@react-pdf-viewer/core/lib/styles/index.css';
import '@react-pdf-viewer/default-layout/lib/styles/index.css';
import '@react-pdf-viewer/page-navigation/lib/styles/index.css';

interface Props {
  fileUrl: string;
  activePage?: number;
}

export default function PDFViewerClient({ fileUrl, activePage }: Props) {
  const defaultLayoutPluginInstance = defaultLayoutPlugin();
  const pageNavigationPluginInstance = pageNavigationPlugin();

  const { jumpToPage } = pageNavigationPluginInstance;

  useEffect(() => {
    if (activePage && activePage >= 1) {
      const timer = setTimeout(() => {
        jumpToPage(activePage - 1);
      }, 300);

      return () => clearTimeout(timer);
    }
  }, [activePage, jumpToPage]);

  return (
    <div className="h-full w-full">
      <Worker workerUrl="https://unpkg.com/pdfjs-dist@3.11.174/build/pdf.worker.min.js">
        <Viewer
          fileUrl={fileUrl}
          plugins={[defaultLayoutPluginInstance, pageNavigationPluginInstance]}
        />
      </Worker>
    </div>
  );
}
