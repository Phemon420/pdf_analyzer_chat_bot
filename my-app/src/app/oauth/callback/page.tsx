'use client';

import { useEffect } from 'react';
import { useSearchParams } from 'next/navigation';

export default function OAuthCallbackPage() {
    const searchParams = useSearchParams();

    useEffect(() => {
        const success = searchParams.get('success');
        const error = searchParams.get('error');

        if (window.opener) {
            // Send message to parent window
            if (success) {
                window.opener.postMessage({ type: 'GOOGLE_OAUTH_SUCCESS' }, '*');
            } else if (error) {
                window.opener.postMessage({ type: 'GOOGLE_OAUTH_ERROR', error }, '*');
            }

            // Close the popup after a short delay
            setTimeout(() => {
                window.close();
            }, 1000);
        } else {
            // If not in popup, redirect to chat page
            setTimeout(() => {
                window.location.href = '/chat';
            }, 2000);
        }
    }, [searchParams]);

    const success = searchParams.get('success');
    const error = searchParams.get('error');

    return (
        <div className="min-h-screen flex items-center justify-center bg-white dark:bg-black">
            <div className="text-center p-8">
                {success ? (
                    <>
                        <div className="text-6xl mb-4">✓</div>
                        <h1 className="text-2xl font-bold text-green-600 dark:text-green-400 mb-2">
                            Google Connected!
                        </h1>
                        <p className="text-gray-600 dark:text-gray-400">
                            You can close this window now.
                        </p>
                    </>
                ) : error ? (
                    <>
                        <div className="text-6xl mb-4">✗</div>
                        <h1 className="text-2xl font-bold text-red-600 dark:text-red-400 mb-2">
                            Connection Failed
                        </h1>
                        <p className="text-gray-600 dark:text-gray-400">
                            Error: {error}
                        </p>
                    </>
                ) : (
                    <>
                        <div className="text-6xl mb-4 animate-spin">⟳</div>
                        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
                            Processing...
                        </h1>
                        <p className="text-gray-600 dark:text-gray-400">
                            Please wait while we complete the connection.
                        </p>
                    </>
                )}
            </div>
        </div>
    );
}
