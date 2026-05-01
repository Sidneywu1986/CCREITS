/**
 * <reit-chart> — ECharts wrapper
 * Usage: <reit-chart option='{...}' style="width:100%;height:300px"></reit-chart>
 */

class ReitChart extends HTMLElement {
  static get observedAttributes() {
    return ['option'];
  }

  connectedCallback() {
    this._render();
    if (typeof ResizeObserver !== 'undefined') {
      this._resizeObserver = new ResizeObserver(() => this._resize());
      this._resizeObserver.observe(this);
    }
  }

  disconnectedCallback() {
    this._resizeObserver?.disconnect();
    this._chart?.dispose();
  }

  attributeChangedCallback(name, oldVal, newVal) {
    if (name === 'option' && oldVal !== newVal) {
      this._render();
    }
  }

  _render() {
    if (typeof echarts === 'undefined') {
      this.textContent = '[ECharts not loaded]';
      return;
    }
    if (!this._chart) {
      this._chart = echarts.init(this);
    }
    try {
      const option = JSON.parse(this.getAttribute('option') || '{}');
      this._chart.setOption(option, true);
    } catch (e) {
      this.textContent = '[Invalid chart option]';
    }
  }

  _resize() {
    this._chart?.resize();
  }
}

customElements.define('reit-chart', ReitChart);
