/**
 * REITs 数据平台 — Icon System v2 (Lucide)
 * 
 * Usage:
 *   ReitIcons.render('search', { size: 16, className: 'text-gray-500' })
 *   ReitIcons.render('trending-up', { size: 20, color: '#ef4444' })
 * 
 * Common icons mapping (Lucide names):
 *   search, home, bar-chart-3, file-text, bell, settings, user,
 *   trending-up, trending-down, arrow-up, arrow-down, plus, minus,
 *   x, check, chevron-down, chevron-up, calendar, clock, filter,
 *   download, upload, refresh-cw, trash-2, edit-2, eye, eye-off,
 *   menu, grid, list, layout-dashboard, pie-chart, wallet,
 *   building-2, warehouse, train-front, zap, leaf, info, alert-circle,
 *   alert-triangle, check-circle, x-circle, help-circle, external-link
 */

const ReitIcons = {
    // Lucide CDN base URL (can be swapped to local if needed)
    CDN: 'https://unpkg.com/lucide@latest',

    /**
     * Render an icon as SVG string (safe for innerHTML after escaping)
     * @param {string} name - Lucide icon name (kebab-case)
     * @param {Object} opts - Options
     * @param {number} opts.size - Icon size in px (default: 16)
     * @param {string} opts.className - Additional CSS classes
     * @param {string} opts.color - Stroke color
     * @param {number} opts.strokeWidth - Stroke width (default: 2)
     * @returns {string} SVG HTML string
     */
    render(name, opts = {}) {
        const size = opts.size || 16;
        const cls = opts.className || '';
        const color = opts.color ? `color: ${opts.color};` : '';
        const strokeWidth = opts.strokeWidth || 2;
        
        // Use Lucide's createIcons API if available, otherwise fallback to placeholder
        if (typeof lucide !== 'undefined' && lucide.icons && lucide.icons[name]) {
            const icon = lucide.icons[name];
            const attrs = [
                `xmlns="http://www.w3.org/2000/svg"`,
                `width="${size}"`,
                `height="${size}"`,
                `viewBox="0 0 24 24"`,
                `fill="none"`,
                `stroke="currentColor"`,
                `stroke-width="${strokeWidth}"`,
                `stroke-linecap="round"`,
                `stroke-linejoin="round"`,
                `class="lucide lucide-${name} ${cls}"`,
                color ? `style="${color}"` : '',
            ].filter(Boolean).join(' ');
            
            return `<svg ${attrs}>${icon.toSvg ? icon.toSvg() : ''}</svg>`;
        }
        
        // Fallback: return a generic circle icon if Lucide not loaded yet
        return `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="${strokeWidth}" stroke-linecap="round" stroke-linejoin="round" class="lucide ${cls}" style="${color}"><circle cx="12" cy="12" r="10"/></svg>`;
    },

    /**
     * Create an icon element (safer: returns DOM node, no innerHTML needed)
     * @param {string} name - Lucide icon name
     * @param {Object} opts - Same as render()
     * @returns {SVGElement}
     */
    create(name, opts = {}) {
        const size = opts.size || 16;
        const cls = opts.className || '';
        const color = opts.color || '';
        const strokeWidth = opts.strokeWidth || 2;

        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('width', size);
        svg.setAttribute('height', size);
        svg.setAttribute('viewBox', '0 0 24 24');
        svg.setAttribute('fill', 'none');
        svg.setAttribute('stroke', 'currentColor');
        svg.setAttribute('stroke-width', strokeWidth);
        svg.setAttribute('stroke-linecap', 'round');
        svg.setAttribute('stroke-linejoin', 'round');
        svg.classList.add('lucide', `lucide-${name}`, ...cls.split(' ').filter(Boolean));
        if (color) svg.style.color = color;

        // If lucide is loaded, use its icon data
        if (typeof lucide !== 'undefined' && lucide.icons && lucide.icons[name]) {
            const iconData = lucide.icons[name];
            // Lucide icons are stored as arrays of tag/attrs pairs
            if (Array.isArray(iconData)) {
                iconData.forEach(([tag, attrs]) => {
                    const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
                    Object.entries(attrs || {}).forEach(([k, v]) => el.setAttribute(k, v));
                    svg.appendChild(el);
                });
            }
        }

        return svg;
    },

    /**
     * Initialize all elements with [data-lucide] attribute
     * Call this after DOM ready and Lucide loaded.
     */
    init(container = document) {
        if (typeof lucide === 'undefined') {
            console.warn('[ReitIcons] Lucide library not loaded yet');
            return;
        }
        const targets = container.querySelectorAll('[data-lucide]');
        targets.forEach(el => {
            const name = el.getAttribute('data-lucide');
            if (!name) return;
            const size = el.getAttribute('data-size') || 16;
            const cls = el.getAttribute('data-class') || '';
            const color = el.getAttribute('data-color') || '';
            
            const icon = this.create(name, {
                size: parseInt(size, 10),
                className: cls,
                color: color
            });
            
            // Replace element or append based on tag
            if (el.tagName === 'I' || el.tagName === 'SPAN') {
                el.replaceWith(icon);
            } else {
                el.innerHTML = '';
                el.appendChild(icon);
            }
        });
    },

    // ── Common icon presets ──
    presets: {
        search(size = 16)      { return this.create('search', { size }); },
        home(size = 16)        { return this.create('home', { size }); },
        chart(size = 16)       { return this.create('bar-chart-3', { size }); },
        file(size = 16)        { return this.create('file-text', { size }); },
        bell(size = 16)        { return this.create('bell', { size }); },
        settings(size = 16)    { return this.create('settings', { size }); },
        user(size = 16)        { return this.create('user', { size }); },
        up(size = 16)          { return this.create('trending-up', { size, color: '#ef4444' }); },
        down(size = 16)        { return this.create('trending-down', { size, color: '#16a34a' }); },
        plus(size = 16)        { return this.create('plus', { size }); },
        minus(size = 16)       { return this.create('minus', { size }); },
        close(size = 16)       { return this.create('x', { size }); },
        check(size = 16)       { return this.create('check', { size }); },
        calendar(size = 16)    { return this.create('calendar', { size }); },
        filter(size = 16)      { return this.create('filter', { size }); },
        download(size = 16)    { return this.create('download', { size }); },
        upload(size = 16)      { return this.create('upload', { size }); },
        refresh(size = 16)     { return this.create('refresh-cw', { size }); },
        trash(size = 16)       { return this.create('trash-2', { size }); },
        edit(size = 16)        { return this.create('edit-2', { size }); },
        eye(size = 16)         { return this.create('eye', { size }); },
        eyeOff(size = 16)      { return this.create('eye-off', { size }); },
        menu(size = 16)        { return this.create('menu', { size }); },
        grid(size = 16)        { return this.create('grid', { size }); },
        list(size = 16)        { return this.create('list', { size }); },
        dashboard(size = 16)   { return this.create('layout-dashboard', { size }); },
        pie(size = 16)         { return this.create('pie-chart', { size }); },
        wallet(size = 16)      { return this.create('wallet', { size }); },
        building(size = 16)    { return this.create('building-2', { size }); },
        warehouse(size = 16)   { return this.create('warehouse', { size }); },
        train(size = 16)       { return this.create('train-front', { size }); },
        zap(size = 16)         { return this.create('zap', { size }); },
        leaf(size = 16)        { return this.create('leaf', { size }); },
        info(size = 16)        { return this.create('info', { size }); },
        alert(size = 16)       { return this.create('alert-circle', { size }); },
        warning(size = 16)     { return this.create('alert-triangle', { size }); },
        success(size = 16)     { return this.create('check-circle', { size }); },
        error(size = 16)       { return this.create('x-circle', { size }); },
        help(size = 16)        { return this.create('help-circle', { size }); },
        external(size = 16)    { return this.create('external-link', { size }); },
    }
};

// Auto-init on DOMContentLoaded if lucide is available
document.addEventListener('DOMContentLoaded', () => {
    // Try to init after a short delay to allow Lucide CDN to load
    setTimeout(() => ReitIcons.init(), 100);
});
