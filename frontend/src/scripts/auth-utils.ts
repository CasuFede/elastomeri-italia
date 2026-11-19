/**
 * auth-utils.ts - Utility condivise per gestione password, visibilità e validazione
 */

export interface PasswordValidationResult {
    isValid: boolean;
    minLength: boolean;
    hasUpper: boolean;
    hasLower: boolean;
    hasNumber: boolean;
    matchesConfirm?: boolean;
}

export const EYE_OPEN_SVG = `<svg class="w-4 h-4 text-zinc-400 hover:text-zinc-200 transition" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg>`;

export const EYE_OFF_SVG = `<svg class="w-4 h-4 text-zinc-400 hover:text-zinc-200 transition" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l18 18" /></svg>`;

/**
 * Valida i requisiti di sicurezza di una password
 */
export function validatePasswordSecurity(
    pwd: string,
    confirmPwd?: string,
    minLen: number = 8
): PasswordValidationResult {
    const minLength = pwd.length >= minLen;
    const hasUpper = /[A-Z]/.test(pwd);
    const hasLower = /[a-z]/.test(pwd);
    const hasNumber = /[0-9]/.test(pwd);
    const matchesConfirm = confirmPwd !== undefined ? pwd === confirmPwd : true;

    const isValid = minLength && hasUpper && hasLower && hasNumber && matchesConfirm;

    return {
        isValid,
        minLength,
        hasUpper,
        hasLower,
        hasNumber,
        matchesConfirm,
    };
}

/**
 * Genera una password sicura lato client
 */
export function generateRandomPassword(length: number = 14): string {
    const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789!@#$%&*';
    let result = '';
    const array = new Uint32Array(length);
    crypto.getRandomValues(array);
    for (let i = 0; i < length; i++) {
        result += chars[array[i] % chars.length];
    }
    return result;
}

/**
 * Attiva il toggle visibilità password (mostra/nascondi) su un campo input
 */
export function setupPasswordToggle(inputId: string, buttonId: string): void {
    const input = document.getElementById(inputId) as HTMLInputElement | null;
    const button = document.getElementById(buttonId) as HTMLButtonElement | null;
    if (!input || !button) return;

    button.innerHTML = input.type === 'password' ? EYE_OPEN_SVG : EYE_OFF_SVG;

    button.addEventListener('click', (e) => {
        e.preventDefault();
        const isPassword = input.type === 'password';
        input.type = isPassword ? 'text' : 'password';
        button.innerHTML = isPassword ? EYE_OFF_SVG : EYE_OPEN_SVG;
        const newTitle = isPassword ? 'Nascondi password' : 'Mostra password';
        button.setAttribute('title', newTitle);
        button.setAttribute('aria-label', newTitle);
        input.focus();
    });
}
