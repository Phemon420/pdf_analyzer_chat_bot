'use client';

import React, { useState, useEffect } from 'react';
import { authService } from '../../lib/api/authService';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || '';

interface GoogleAuthButtonProps {
    className?: string;
}

export function GoogleAuthButton({ className = '' }: GoogleAuthButtonProps) {
    const [isConnected, setIsConnected] = useState(false);
    const [isLoading, setIsLoading] = useState(true);
    const [isConnecting, setIsConnecting] = useState(false);

    // Check connection status on mount
    useEffect(() => {
        checkConnectionStatus();
    }, []);

    // Listen for OAuth callback messages from popup
    useEffect(() => {
        const handleMessage = (event: MessageEvent) => {
            if (event.data.type === 'GOOGLE_OAUTH_SUCCESS') {
                setIsConnected(true);
                setIsConnecting(false);
            } else if (event.data.type === 'GOOGLE_OAUTH_ERROR') {
                console.error('OAuth error:', event.data.error);
                setIsConnecting(false);
            }
        };

        window.addEventListener('message', handleMessage);
        return () => window.removeEventListener('message', handleMessage);
    }, []);

    const checkConnectionStatus = async () => {
        try {
            const token = authService.getToken();
            if (!token) {
                setIsLoading(false);
                return;
            }

            const response = await fetch(`${API_BASE_URL}/oauth/google/status`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                },
            });

            const data = await response.json();
            setIsConnected(data.connected || false);
        } catch (error) {
            console.error('Error checking Google connection:', error);
        } finally {
            setIsLoading(false);
        }
    };

    const handleConnect = async () => {
        try {
            setIsConnecting(true);
            const token = authService.getToken();

            if (!token) {
                alert('Please log in first to connect your Google account');
                setIsConnecting(false);
                return;
            }

            // Get OAuth URL from backend
            const response = await fetch(`${API_BASE_URL}/oauth/google/url`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                },
            });

            const data = await response.json();

            if (data.status !== 1 || !data.url) {
                throw new Error(data.message || 'Failed to get OAuth URL');
            }

            // Open OAuth popup
            const width = 500;
            const height = 600;
            const left = window.screenX + (window.outerWidth - width) / 2;
            const top = window.screenY + (window.outerHeight - height) / 2;

            const popup = window.open(
                data.url,
                'Google OAuth',
                `width=${width},height=${height},left=${left},top=${top}`
            );

            // Poll for popup closure
            const checkPopup = setInterval(() => {
                if (popup?.closed) {
                    clearInterval(checkPopup);
                    // Re-check connection status after popup closes
                    setTimeout(() => {
                        checkConnectionStatus();
                        setIsConnecting(false);
                    }, 1000);
                }
            }, 500);

        } catch (error) {
            console.error('Error connecting to Google:', error);
            setIsConnecting(false);
        }
    };

    const handleDisconnect = async () => {
        if (!confirm('Are you sure you want to disconnect your Google account?')) {
            return;
        }

        try {
            const token = authService.getToken();

            const response = await fetch(`${API_BASE_URL}/oauth/google/revoke`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                },
            });

            const data = await response.json();

            if (data.status === 1) {
                setIsConnected(false);
            }
        } catch (error) {
            console.error('Error disconnecting Google:', error);
        }
    };

    if (isLoading) {
        return (
            <button
                disabled
                className={`flex items-center gap-2 px-3 py-1.5 text-sm rounded-md bg-gray-100 dark:bg-gray-800 text-gray-400 ${className}`}
            >
                <GoogleIcon />
                <span>Loading...</span>
            </button>
        );
    }

    if (isConnected) {
        return (
            <button
                onClick={handleDisconnect}
                className={`flex items-center gap-2 px-3 py-1.5 text-sm rounded-md bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 hover:bg-green-200 dark:hover:bg-green-900/50 transition-colors ${className}`}
                title="Click to disconnect"
            >
                <GoogleIcon />
                <span>Connected</span>
                <CheckIcon />
            </button>
        );
    }

    return (
        <button
            onClick={handleConnect}
            disabled={isConnecting}
            className={`flex items-center gap-2 px-3 py-1.5 text-sm rounded-md bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors disabled:opacity-50 ${className}`}
        >
            <GoogleIcon />
            <span>{isConnecting ? 'Connecting...' : 'Connect Google'}</span>
        </button>
    );
}

function GoogleIcon() {
    return (
        <svg width="16" height="16" viewBox="0 0 24 24">
            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
        </svg>
    );
}

function CheckIcon() {
    return (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="20,6 9,17 4,12"></polyline>
        </svg>
    );
}
