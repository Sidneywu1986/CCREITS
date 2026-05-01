/**
 * Environment verification — confirms jsdom supports Custom Elements v1
 */

describe('Web Components environment', () => {
  it('should support customElements registry', () => {
    expect(window.customElements).toBeDefined();
    expect(typeof customElements.define).toBe('function');
  });

  it('should render a basic custom element', () => {
    class HelloWorld extends HTMLElement {
      connectedCallback() {
        this.textContent = 'hello';
      }
    }
    customElements.define('hello-world', HelloWorld);

    const el = document.createElement('hello-world');
    document.body.appendChild(el);
    expect(el.textContent).toBe('hello');
  });
});
