/**
 * Shared API utilities for Zelia citizen portal.
 * Attaches JWT bearer token and role header to all fetch requests.
 */

export const getAuthHeaders = () => {
    const token = localStorage.getItem('zelia_jwt');
    return {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        'x-user-role': 'citizen'
    };
};

/**
 * SHA-256 hash a string using the browser SubtleCrypto API.
 * Used to hash Aadhaar before sending to auth service.
 */
export const sha256 = async (str) => {
    const buf = await window.crypto.subtle.digest(
        'SHA-256',
        new TextEncoder().encode(str)
    );
    return Array.from(new Uint8Array(buf))
        .map(b => b.toString(16).padStart(2, '0'))
        .join('');
};
