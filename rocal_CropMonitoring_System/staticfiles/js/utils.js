// utils.js - 공통 유틸리티 함수

/**
 * NaN, Infinity 등을 안전하게 처리하는 JSON 파싱 함수
 * Docker 환경에서 백엔드가 NaN을 반환할 때 발생하는 파싱 에러 방지
 */
async function safeFetchJson(url) {
    const response = await fetch(url);
    const text = await response.text();

    // NaN, Infinity, -Infinity를 null로 치환
    const sanitized = text
        .replace(/:\s*NaN\b/g, ': null')
        .replace(/:\s*Infinity\b/g, ': null')
        .replace(/:\s*-Infinity\b/g, ': null')
        .replace(/\bNaN\b/g, 'null')
        .replace(/\bInfinity\b/g, 'null')
        .replace(/\b-Infinity\b/g, 'null');

    return JSON.parse(sanitized);
}

/**
 * 배열 내의 NaN, null, undefined를 제거하거나 기본값으로 치환
 */
function sanitizeArray(arr, defaultValue = 0) {
    if (!Array.isArray(arr)) return [];
    return arr.map(val => {
        if (val === null || val === undefined || Number.isNaN(val)) {
            return defaultValue;
        }
        return val;
    });
}

/**
 * 객체 내의 모든 NaN 값을 null로 치환
 */
function sanitizeObject(obj) {
    if (obj === null || typeof obj !== 'object') return obj;

    if (Array.isArray(obj)) {
        return obj.map(item => sanitizeObject(item));
    }

    const result = {};
    for (const key in obj) {
        const value = obj[key];
        if (Number.isNaN(value) || value === Infinity || value === -Infinity) {
            result[key] = null;
        } else if (typeof value === 'object') {
            result[key] = sanitizeObject(value);
        } else {
            result[key] = value;
        }
    }
    return result;
}
