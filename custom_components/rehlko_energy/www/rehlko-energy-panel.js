// node_modules/@lit/reactive-element/css-tag.js
var e = globalThis, t = e.ShadowRoot && (e.ShadyCSS === void 0 || e.ShadyCSS.nativeShadow) && "adoptedStyleSheets" in Document.prototype && "replace" in CSSStyleSheet.prototype, n = Symbol(), r = /* @__PURE__ */ new WeakMap(), i = class {
	constructor(e, t, r) {
		if (this._$cssResult$ = !0, r !== n) throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");
		this.cssText = e, this.t = t;
	}
	get styleSheet() {
		let e = this.o, n = this.t;
		if (t && e === void 0) {
			let t = n !== void 0 && n.length === 1;
			t && (e = r.get(n)), e === void 0 && ((this.o = e = new CSSStyleSheet()).replaceSync(this.cssText), t && r.set(n, e));
		}
		return e;
	}
	toString() {
		return this.cssText;
	}
}, a = (e) => new i(typeof e == "string" ? e : e + "", void 0, n), o = (e, ...t) => new i(e.length === 1 ? e[0] : t.reduce((t, n, r) => t + ((e) => {
	if (!0 === e._$cssResult$) return e.cssText;
	if (typeof e == "number") return e;
	throw Error("Value passed to 'css' function must be a 'css' function result: " + e + ". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.");
})(n) + e[r + 1], e[0]), e, n), s = (n, r) => {
	if (t) n.adoptedStyleSheets = r.map((e) => e instanceof CSSStyleSheet ? e : e.styleSheet);
	else for (let t of r) {
		let r = document.createElement("style"), i = e.litNonce;
		i !== void 0 && r.setAttribute("nonce", i), r.textContent = t.cssText, n.appendChild(r);
	}
}, c = t ? (e) => e : (e) => e instanceof CSSStyleSheet ? ((e) => {
	let t = "";
	for (let n of e.cssRules) t += n.cssText;
	return a(t);
})(e) : e, { is: l, defineProperty: u, getOwnPropertyDescriptor: ee, getOwnPropertyNames: te, getOwnPropertySymbols: ne, getPrototypeOf: re } = Object, d = globalThis, ie = d.trustedTypes, ae = ie ? ie.emptyScript : "", oe = d.reactiveElementPolyfillSupport, f = (e, t) => e, p = {
	toAttribute(e, t) {
		switch (t) {
			case Boolean:
				e = e ? ae : null;
				break;
			case Object:
			case Array: e = e == null ? e : JSON.stringify(e);
		}
		return e;
	},
	fromAttribute(e, t) {
		let n = e;
		switch (t) {
			case Boolean:
				n = e !== null;
				break;
			case Number:
				n = e === null ? null : Number(e);
				break;
			case Object:
			case Array: try {
				n = JSON.parse(e);
			} catch {
				n = null;
			}
		}
		return n;
	}
}, se = (e, t) => !l(e, t), ce = {
	attribute: !0,
	type: String,
	converter: p,
	reflect: !1,
	useDefault: !1,
	hasChanged: se
};
Symbol.metadata ??= Symbol("metadata"), d.litPropertyMetadata ??= /* @__PURE__ */ new WeakMap();
var m = class extends HTMLElement {
	static addInitializer(e) {
		this._$Ei(), (this.l ??= []).push(e);
	}
	static get observedAttributes() {
		return this.finalize(), this._$Eh && [...this._$Eh.keys()];
	}
	static createProperty(e, t = ce) {
		if (t.state && (t.attribute = !1), this._$Ei(), this.prototype.hasOwnProperty(e) && ((t = Object.create(t)).wrapped = !0), this.elementProperties.set(e, t), !t.noAccessor) {
			let n = Symbol(), r = this.getPropertyDescriptor(e, n, t);
			r !== void 0 && u(this.prototype, e, r);
		}
	}
	static getPropertyDescriptor(e, t, n) {
		let { get: r, set: i } = ee(this.prototype, e) ?? {
			get() {
				return this[t];
			},
			set(e) {
				this[t] = e;
			}
		};
		return {
			get: r,
			set(t) {
				let a = r?.call(this);
				i?.call(this, t), this.requestUpdate(e, a, n);
			},
			configurable: !0,
			enumerable: !0
		};
	}
	static getPropertyOptions(e) {
		return this.elementProperties.get(e) ?? ce;
	}
	static _$Ei() {
		if (this.hasOwnProperty(f("elementProperties"))) return;
		let e = re(this);
		e.finalize(), e.l !== void 0 && (this.l = [...e.l]), this.elementProperties = new Map(e.elementProperties);
	}
	static finalize() {
		if (this.hasOwnProperty(f("finalized"))) return;
		if (this.finalized = !0, this._$Ei(), this.hasOwnProperty(f("properties"))) {
			let e = this.properties, t = [...te(e), ...ne(e)];
			for (let n of t) this.createProperty(n, e[n]);
		}
		let e = this[Symbol.metadata];
		if (e !== null) {
			let t = litPropertyMetadata.get(e);
			if (t !== void 0) for (let [e, n] of t) this.elementProperties.set(e, n);
		}
		this._$Eh = /* @__PURE__ */ new Map();
		for (let [e, t] of this.elementProperties) {
			let n = this._$Eu(e, t);
			n !== void 0 && this._$Eh.set(n, e);
		}
		this.elementStyles = this.finalizeStyles(this.styles);
	}
	static finalizeStyles(e) {
		let t = [];
		if (Array.isArray(e)) {
			let n = new Set(e.flat(1 / 0).reverse());
			for (let e of n) t.unshift(c(e));
		} else e !== void 0 && t.push(c(e));
		return t;
	}
	static _$Eu(e, t) {
		let n = t.attribute;
		return !1 === n ? void 0 : typeof n == "string" ? n : typeof e == "string" ? e.toLowerCase() : void 0;
	}
	constructor() {
		super(), this._$Ep = void 0, this.isUpdatePending = !1, this.hasUpdated = !1, this._$Em = null, this._$Ev();
	}
	_$Ev() {
		this._$ES = new Promise((e) => this.enableUpdating = e), this._$AL = /* @__PURE__ */ new Map(), this._$E_(), this.requestUpdate(), this.constructor.l?.forEach((e) => e(this));
	}
	addController(e) {
		(this._$EO ??= /* @__PURE__ */ new Set()).add(e), this.renderRoot !== void 0 && this.isConnected && e.hostConnected?.();
	}
	removeController(e) {
		this._$EO?.delete(e);
	}
	_$E_() {
		let e = /* @__PURE__ */ new Map(), t = this.constructor.elementProperties;
		for (let n of t.keys()) this.hasOwnProperty(n) && (e.set(n, this[n]), delete this[n]);
		e.size > 0 && (this._$Ep = e);
	}
	createRenderRoot() {
		let e = this.shadowRoot ?? this.attachShadow(this.constructor.shadowRootOptions);
		return s(e, this.constructor.elementStyles), e;
	}
	connectedCallback() {
		this.renderRoot ??= this.createRenderRoot(), this.enableUpdating(!0), this._$EO?.forEach((e) => e.hostConnected?.());
	}
	enableUpdating(e) {}
	disconnectedCallback() {
		this._$EO?.forEach((e) => e.hostDisconnected?.());
	}
	attributeChangedCallback(e, t, n) {
		this._$AK(e, n);
	}
	_$ET(e, t) {
		let n = this.constructor.elementProperties.get(e), r = this.constructor._$Eu(e, n);
		if (r !== void 0 && !0 === n.reflect) {
			let i = (n.converter?.toAttribute === void 0 ? p : n.converter).toAttribute(t, n.type);
			this._$Em = e, i == null ? this.removeAttribute(r) : this.setAttribute(r, i), this._$Em = null;
		}
	}
	_$AK(e, t) {
		let n = this.constructor, r = n._$Eh.get(e);
		if (r !== void 0 && this._$Em !== r) {
			let e = n.getPropertyOptions(r), i = typeof e.converter == "function" ? { fromAttribute: e.converter } : e.converter?.fromAttribute === void 0 ? p : e.converter;
			this._$Em = r;
			let a = i.fromAttribute(t, e.type);
			this[r] = a ?? this._$Ej?.get(r) ?? a, this._$Em = null;
		}
	}
	requestUpdate(e, t, n, r = !1, i) {
		if (e !== void 0) {
			let a = this.constructor;
			if (!1 === r && (i = this[e]), n ??= a.getPropertyOptions(e), !((n.hasChanged ?? se)(i, t) || n.useDefault && n.reflect && i === this._$Ej?.get(e) && !this.hasAttribute(a._$Eu(e, n)))) return;
			this.C(e, t, n);
		}
		!1 === this.isUpdatePending && (this._$ES = this._$EP());
	}
	C(e, t, { useDefault: n, reflect: r, wrapped: i }, a) {
		n && !(this._$Ej ??= /* @__PURE__ */ new Map()).has(e) && (this._$Ej.set(e, a ?? t ?? this[e]), !0 !== i || a !== void 0) || (this._$AL.has(e) || (this.hasUpdated || n || (t = void 0), this._$AL.set(e, t)), !0 === r && this._$Em !== e && (this._$Eq ??= /* @__PURE__ */ new Set()).add(e));
	}
	async _$EP() {
		this.isUpdatePending = !0;
		try {
			await this._$ES;
		} catch (e) {
			Promise.reject(e);
		}
		let e = this.scheduleUpdate();
		return e != null && await e, !this.isUpdatePending;
	}
	scheduleUpdate() {
		return this.performUpdate();
	}
	performUpdate() {
		if (!this.isUpdatePending) return;
		if (!this.hasUpdated) {
			if (this.renderRoot ??= this.createRenderRoot(), this._$Ep) {
				for (let [e, t] of this._$Ep) this[e] = t;
				this._$Ep = void 0;
			}
			let e = this.constructor.elementProperties;
			if (e.size > 0) for (let [t, n] of e) {
				let { wrapped: e } = n, r = this[t];
				!0 !== e || this._$AL.has(t) || r === void 0 || this.C(t, void 0, n, r);
			}
		}
		let e = !1, t = this._$AL;
		try {
			e = this.shouldUpdate(t), e ? (this.willUpdate(t), this._$EO?.forEach((e) => e.hostUpdate?.()), this.update(t)) : this._$EM();
		} catch (t) {
			throw e = !1, this._$EM(), t;
		}
		e && this._$AE(t);
	}
	willUpdate(e) {}
	_$AE(e) {
		this._$EO?.forEach((e) => e.hostUpdated?.()), this.hasUpdated || (this.hasUpdated = !0, this.firstUpdated(e)), this.updated(e);
	}
	_$EM() {
		this._$AL = /* @__PURE__ */ new Map(), this.isUpdatePending = !1;
	}
	get updateComplete() {
		return this.getUpdateComplete();
	}
	getUpdateComplete() {
		return this._$ES;
	}
	shouldUpdate(e) {
		return !0;
	}
	update(e) {
		this._$Eq &&= this._$Eq.forEach((e) => this._$ET(e, this[e])), this._$EM();
	}
	updated(e) {}
	firstUpdated(e) {}
};
m.elementStyles = [], m.shadowRootOptions = { mode: "open" }, m[f("elementProperties")] = /* @__PURE__ */ new Map(), m[f("finalized")] = /* @__PURE__ */ new Map(), oe?.({ ReactiveElement: m }), (d.reactiveElementVersions ??= []).push("2.1.2");
// node_modules/lit-html/lit-html.js
var le = globalThis, ue = (e) => e, h = le.trustedTypes, de = h ? h.createPolicy("lit-html", { createHTML: (e) => e }) : void 0, g = "$lit$", _ = `lit$${Math.random().toFixed(9).slice(2)}$`, v = "?" + _, fe = `<${v}>`, y = document, b = () => y.createComment(""), x = (e) => e === null || typeof e != "object" && typeof e != "function", S = Array.isArray, pe = (e) => S(e) || typeof e?.[Symbol.iterator] == "function", me = "[ 	\n\f\r]", C = /<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g, he = /-->/g, ge = />/g, w = RegExp(`>|${me}(?:([^\\s"'>=/]+)(${me}*=${me}*(?:[^ \t\n\f\r"'\`<>=]|("|')|))|$)`, "g"), _e = /'/g, ve = /"/g, ye = /^(?:script|style|textarea|title)$/i, T = ((e) => (t, ...n) => ({
	_$litType$: e,
	strings: t,
	values: n
}))(1), E = Symbol.for("lit-noChange"), D = Symbol.for("lit-nothing"), be = /* @__PURE__ */ new WeakMap(), O = y.createTreeWalker(y, 129);
function xe(e, t) {
	if (!S(e) || !e.hasOwnProperty("raw")) throw Error("invalid template strings array");
	return de === void 0 ? t : de.createHTML(t);
}
var Se = (e, t) => {
	let n = e.length - 1, r = [], i, a = t === 2 ? "<svg>" : t === 3 ? "<math>" : "", o = C;
	for (let t = 0; t < n; t++) {
		let n = e[t], s, c, l = -1, u = 0;
		for (; u < n.length && (o.lastIndex = u, c = o.exec(n), c !== null);) u = o.lastIndex, o === C ? c[1] === "!--" ? o = he : c[1] === void 0 ? c[2] === void 0 ? c[3] !== void 0 && (o = w) : (ye.test(c[2]) && (i = RegExp("</" + c[2], "g")), o = w) : o = ge : o === w ? c[0] === ">" ? (o = i ?? C, l = -1) : c[1] === void 0 ? l = -2 : (l = o.lastIndex - c[2].length, s = c[1], o = c[3] === void 0 ? w : c[3] === "\"" ? ve : _e) : o === ve || o === _e ? o = w : o === he || o === ge ? o = C : (o = w, i = void 0);
		let ee = o === w && e[t + 1].startsWith("/>") ? " " : "";
		a += o === C ? n + fe : l >= 0 ? (r.push(s), n.slice(0, l) + g + n.slice(l) + _ + ee) : n + _ + (l === -2 ? t : ee);
	}
	return [xe(e, a + (e[n] || "<?>") + (t === 2 ? "</svg>" : t === 3 ? "</math>" : "")), r];
}, k = class e {
	constructor({ strings: t, _$litType$: n }, r) {
		let i;
		this.parts = [];
		let a = 0, o = 0, s = t.length - 1, c = this.parts, [l, u] = Se(t, n);
		if (this.el = e.createElement(l, r), O.currentNode = this.el.content, n === 2 || n === 3) {
			let e = this.el.content.firstChild;
			e.replaceWith(...e.childNodes);
		}
		for (; (i = O.nextNode()) !== null && c.length < s;) {
			if (i.nodeType === 1) {
				if (i.hasAttributes()) for (let e of i.getAttributeNames()) if (e.endsWith(g)) {
					let t = u[o++], n = i.getAttribute(e).split(_), r = /([.?@])?(.*)/.exec(t);
					c.push({
						type: 1,
						index: a,
						name: r[2],
						strings: n,
						ctor: r[1] === "." ? we : r[1] === "?" ? Te : r[1] === "@" ? Ee : M
					}), i.removeAttribute(e);
				} else e.startsWith(_) && (c.push({
					type: 6,
					index: a
				}), i.removeAttribute(e));
				if (ye.test(i.tagName)) {
					let e = i.textContent.split(_), t = e.length - 1;
					if (t > 0) {
						i.textContent = h ? h.emptyScript : "";
						for (let n = 0; n < t; n++) i.append(e[n], b()), O.nextNode(), c.push({
							type: 2,
							index: ++a
						});
						i.append(e[t], b());
					}
				}
			} else if (i.nodeType === 8) {
				if (i.data === v) c.push({
					type: 2,
					index: a
				});
				else {
					let e = -1;
					for (; (e = i.data.indexOf(_, e + 1)) !== -1;) c.push({
						type: 7,
						index: a
					}), e += _.length - 1;
				}
			}
			a++;
		}
	}
	static createElement(e, t) {
		let n = y.createElement("template");
		return n.innerHTML = e, n;
	}
};
function A(e, t, n = e, r) {
	if (t === E) return t;
	let i = r === void 0 ? n._$Cl : n._$Co?.[r], a = x(t) ? void 0 : t._$litDirective$;
	return i?.constructor !== a && (i?._$AO?.(!1), a === void 0 ? i = void 0 : (i = new a(e), i._$AT(e, n, r)), r === void 0 ? n._$Cl = i : (n._$Co ??= [])[r] = i), i !== void 0 && (t = A(e, i._$AS(e, t.values), i, r)), t;
}
var Ce = class {
	constructor(e, t) {
		this._$AV = [], this._$AN = void 0, this._$AD = e, this._$AM = t;
	}
	get parentNode() {
		return this._$AM.parentNode;
	}
	get _$AU() {
		return this._$AM._$AU;
	}
	u(e) {
		let { el: { content: t }, parts: n } = this._$AD, r = (e?.creationScope ?? y).importNode(t, !0);
		O.currentNode = r;
		let i = O.nextNode(), a = 0, o = 0, s = n[0];
		for (; s !== void 0;) {
			if (a === s.index) {
				let t;
				s.type === 2 ? t = new j(i, i.nextSibling, this, e) : s.type === 1 ? t = new s.ctor(i, s.name, s.strings, this, e) : s.type === 6 && (t = new De(i, this, e)), this._$AV.push(t), s = n[++o];
			}
			a !== s?.index && (i = O.nextNode(), a++);
		}
		return O.currentNode = y, r;
	}
	p(e) {
		let t = 0;
		for (let n of this._$AV) n !== void 0 && (n.strings === void 0 ? n._$AI(e[t]) : (n._$AI(e, n, t), t += n.strings.length - 2)), t++;
	}
}, j = class e {
	get _$AU() {
		return this._$AM?._$AU ?? this._$Cv;
	}
	constructor(e, t, n, r) {
		this.type = 2, this._$AH = D, this._$AN = void 0, this._$AA = e, this._$AB = t, this._$AM = n, this.options = r, this._$Cv = r?.isConnected ?? !0;
	}
	get parentNode() {
		let e = this._$AA.parentNode, t = this._$AM;
		return t !== void 0 && e?.nodeType === 11 && (e = t.parentNode), e;
	}
	get startNode() {
		return this._$AA;
	}
	get endNode() {
		return this._$AB;
	}
	_$AI(e, t = this) {
		e = A(this, e, t), x(e) ? e === D || e == null || e === "" ? (this._$AH !== D && this._$AR(), this._$AH = D) : e !== this._$AH && e !== E && this._(e) : e._$litType$ === void 0 ? e.nodeType === void 0 ? pe(e) ? this.k(e) : this._(e) : this.T(e) : this.$(e);
	}
	O(e) {
		return this._$AA.parentNode.insertBefore(e, this._$AB);
	}
	T(e) {
		this._$AH !== e && (this._$AR(), this._$AH = this.O(e));
	}
	_(e) {
		this._$AH !== D && x(this._$AH) ? this._$AA.nextSibling.data = e : this.T(y.createTextNode(e)), this._$AH = e;
	}
	$(e) {
		let { values: t, _$litType$: n } = e, r = typeof n == "number" ? this._$AC(e) : (n.el === void 0 && (n.el = k.createElement(xe(n.h, n.h[0]), this.options)), n);
		if (this._$AH?._$AD === r) this._$AH.p(t);
		else {
			let e = new Ce(r, this), n = e.u(this.options);
			e.p(t), this.T(n), this._$AH = e;
		}
	}
	_$AC(e) {
		let t = be.get(e.strings);
		return t === void 0 && be.set(e.strings, t = new k(e)), t;
	}
	k(t) {
		S(this._$AH) || (this._$AH = [], this._$AR());
		let n = this._$AH, r, i = 0;
		for (let a of t) i === n.length ? n.push(r = new e(this.O(b()), this.O(b()), this, this.options)) : r = n[i], r._$AI(a), i++;
		i < n.length && (this._$AR(r && r._$AB.nextSibling, i), n.length = i);
	}
	_$AR(e = this._$AA.nextSibling, t) {
		for (this._$AP?.(!1, !0, t); e !== this._$AB;) {
			let t = ue(e).nextSibling;
			ue(e).remove(), e = t;
		}
	}
	setConnected(e) {
		this._$AM === void 0 && (this._$Cv = e, this._$AP?.(e));
	}
}, M = class {
	get tagName() {
		return this.element.tagName;
	}
	get _$AU() {
		return this._$AM._$AU;
	}
	constructor(e, t, n, r, i) {
		this.type = 1, this._$AH = D, this._$AN = void 0, this.element = e, this.name = t, this._$AM = r, this.options = i, n.length > 2 || n[0] !== "" || n[1] !== "" ? (this._$AH = Array(n.length - 1).fill(/* @__PURE__ */ new String()), this.strings = n) : this._$AH = D;
	}
	_$AI(e, t = this, n, r) {
		let i = this.strings, a = !1;
		if (i === void 0) e = A(this, e, t, 0), a = !x(e) || e !== this._$AH && e !== E, a && (this._$AH = e);
		else {
			let r = e, o, s;
			for (e = i[0], o = 0; o < i.length - 1; o++) s = A(this, r[n + o], t, o), s === E && (s = this._$AH[o]), a ||= !x(s) || s !== this._$AH[o], s === D ? e = D : e !== D && (e += (s ?? "") + i[o + 1]), this._$AH[o] = s;
		}
		a && !r && this.j(e);
	}
	j(e) {
		e === D ? this.element.removeAttribute(this.name) : this.element.setAttribute(this.name, e ?? "");
	}
}, we = class extends M {
	constructor() {
		super(...arguments), this.type = 3;
	}
	j(e) {
		this.element[this.name] = e === D ? void 0 : e;
	}
}, Te = class extends M {
	constructor() {
		super(...arguments), this.type = 4;
	}
	j(e) {
		this.element.toggleAttribute(this.name, !!e && e !== D);
	}
}, Ee = class extends M {
	constructor(e, t, n, r, i) {
		super(e, t, n, r, i), this.type = 5;
	}
	_$AI(e, t = this) {
		if ((e = A(this, e, t, 0) ?? D) === E) return;
		let n = this._$AH, r = e === D && n !== D || e.capture !== n.capture || e.once !== n.once || e.passive !== n.passive, i = e !== D && (n === D || r);
		r && this.element.removeEventListener(this.name, this, n), i && this.element.addEventListener(this.name, this, e), this._$AH = e;
	}
	handleEvent(e) {
		typeof this._$AH == "function" ? this._$AH.call(this.options?.host ?? this.element, e) : this._$AH.handleEvent(e);
	}
}, De = class {
	constructor(e, t, n) {
		this.element = e, this.type = 6, this._$AN = void 0, this._$AM = t, this.options = n;
	}
	get _$AU() {
		return this._$AM._$AU;
	}
	_$AI(e) {
		A(this, e);
	}
}, Oe = {
	M: g,
	P: _,
	A: v,
	C: 1,
	L: Se,
	R: Ce,
	D: pe,
	V: A,
	I: j,
	H: M,
	N: Te,
	U: Ee,
	B: we,
	F: De
}, ke = le.litHtmlPolyfillSupport;
ke?.(k, j), (le.litHtmlVersions ??= []).push("3.3.3");
var Ae = (e, t, n) => {
	let r = n?.renderBefore ?? t, i = r._$litPart$;
	if (i === void 0) {
		let e = n?.renderBefore ?? null;
		r._$litPart$ = i = new j(t.insertBefore(b(), e), e, void 0, n ?? {});
	}
	return i._$AI(e), i;
}, N = globalThis, P = class extends m {
	constructor() {
		super(...arguments), this.renderOptions = { host: this }, this._$Do = void 0;
	}
	createRenderRoot() {
		let e = super.createRenderRoot();
		return this.renderOptions.renderBefore ??= e.firstChild, e;
	}
	update(e) {
		let t = this.render();
		this.hasUpdated || (this.renderOptions.isConnected = this.isConnected), super.update(e), this._$Do = Ae(t, this.renderRoot, this.renderOptions);
	}
	connectedCallback() {
		super.connectedCallback(), this._$Do?.setConnected(!0);
	}
	disconnectedCallback() {
		super.disconnectedCallback(), this._$Do?.setConnected(!1);
	}
	render() {
		return E;
	}
};
P._$litElement$ = !0, P.finalized = !0, N.litElementHydrateSupport?.({ LitElement: P });
var je = N.litElementPolyfillSupport;
je?.({ LitElement: P }), (N.litElementVersions ??= []).push("4.2.2");
// node_modules/@lit/reactive-element/decorators/custom-element.js
var Me = (e) => (t, n) => {
	n === void 0 ? customElements.define(e, t) : n.addInitializer(() => {
		customElements.define(e, t);
	});
}, Ne = {
	attribute: !0,
	type: String,
	converter: p,
	reflect: !1,
	hasChanged: se
}, Pe = (e = Ne, t, n) => {
	let { kind: r, metadata: i } = n, a = globalThis.litPropertyMetadata.get(i);
	if (a === void 0 && globalThis.litPropertyMetadata.set(i, a = /* @__PURE__ */ new Map()), r === "setter" && ((e = Object.create(e)).wrapped = !0), a.set(n.name, e), r === "accessor") {
		let { name: r } = n;
		return {
			set(n) {
				let i = t.get.call(this);
				t.set.call(this, n), this.requestUpdate(r, i, e, !0, n);
			},
			init(t) {
				return t !== void 0 && this.C(r, void 0, e, t), t;
			}
		};
	}
	if (r === "setter") {
		let { name: r } = n;
		return function(n) {
			let i = this[r];
			t.call(this, n), this.requestUpdate(r, i, e, !0, n);
		};
	}
	throw Error("Unsupported decorator location: " + r);
};
function F(e) {
	return (t, n) => typeof n == "object" ? Pe(e, t, n) : ((e, t, n) => {
		let r = t.hasOwnProperty(n);
		return t.constructor.createProperty(n, e), r ? Object.getOwnPropertyDescriptor(t, n) : void 0;
	})(e, t, n);
}
// node_modules/@lit/reactive-element/decorators/state.js
function I(e) {
	return F({
		...e,
		state: !0,
		attribute: !1
	});
}
// node_modules/lit-html/directive.js
var L = {
	ATTRIBUTE: 1,
	CHILD: 2,
	PROPERTY: 3,
	BOOLEAN_ATTRIBUTE: 4,
	EVENT: 5,
	ELEMENT: 6
}, Fe = (e) => (...t) => ({
	_$litDirective$: e,
	values: t
}), Ie = class {
	constructor(e) {}
	get _$AU() {
		return this._$AM._$AU;
	}
	_$AT(e, t, n) {
		this._$Ct = e, this._$AM = t, this._$Ci = n;
	}
	_$AS(e, t) {
		return this.update(e, t);
	}
	update(e, t) {
		return this.render(...t);
	}
}, { I: Le } = Oe, Re = (e) => e.strings === void 0, ze = {}, Be = (e, t = ze) => e._$AH = t, Ve = Fe(class extends Ie {
	constructor() {
		super(...arguments), this.key = D;
	}
	render(e, t) {
		return this.key = e, t;
	}
	update(e, [t, n]) {
		return t !== this.key && (Be(e), this.key = t), n;
	}
}), He = Fe(class extends Ie {
	constructor(e) {
		if (super(e), e.type !== L.PROPERTY && e.type !== L.ATTRIBUTE && e.type !== L.BOOLEAN_ATTRIBUTE) throw Error("The `live` directive is not allowed on child or event bindings");
		if (!Re(e)) throw Error("`live` bindings can only contain a single expression");
	}
	render(e) {
		return e;
	}
	update(e, [t]) {
		if (t === E || t === D) return t;
		let n = e.element, r = e.name;
		if (e.type === L.PROPERTY) {
			if (t === n[r]) return E;
		} else if (e.type === L.BOOLEAN_ATTRIBUTE) {
			if (!!t === n.hasAttribute(r)) return E;
		} else if (e.type === L.ATTRIBUTE && n.getAttribute(r) === t + "") return E;
		return Be(e), t;
	}
}), Ue = "M11,15H13V17H11V15M11,7H13V13H11V7M12,2C6.47,2 2,6.5 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M12,20A8,8 0 0,1 4,12A8,8 0 0,1 12,4A8,8 0 0,1 20,12A8,8 0 0,1 12,20Z", We = "M13 13H11V7H13M11 15H13V17H11M15.73 3H8.27L3 8.27V15.73L8.27 21H15.73L21 15.73V8.27L15.73 3Z", Ge = "M19,3H18V1H16V3H8V1H6V3H5A2,2 0 0,0 3,5V19A2,2 0 0,0 5,21H10V19H5V8H19V9H21V5A2,2 0 0,0 19,3M21.7,13.35L20.7,14.35L18.65,12.35L19.65,11.35C19.85,11.14 20.19,11.13 20.42,11.35L21.7,12.63C21.89,12.83 21.89,13.15 21.7,13.35M12,18.94L18.07,12.88L20.12,14.88L14.06,21H12V18.94Z", Ke = "M19,19H5V8H19M19,3H18V1H16V3H8V1H6V3H5C3.89,3 3,3.9 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V5A2,2 0 0,0 19,3M9.31,17L11.75,14.56L14.19,17L15.25,15.94L12.81,13.5L15.25,11.06L14.19,10L11.75,12.44L9.31,10L8.25,11.06L10.69,13.5L8.25,15.94L9.31,17Z", qe = "M11,15H13V17H11V15M11,7H13V13H11V7M12,3A9,9 0 0,0 3,12A9,9 0 0,0 12,21A9,9 0 0,0 21,12A9,9 0 0,0 12,3M12,19C8.14,19 5,15.86 5,12C5,8.14 8.14,5 12,5C15.86,5 19,8.14 19,12C19,15.86 15.86,19 12,19M20.5,20.5C22.66,18.31 24,15.31 24,12C24,8.69 22.66,5.69 20.5,3.5L19.42,4.58C21.32,6.5 22.5,9.11 22.5,12C22.5,14.9 21.32,17.5 19.42,19.42L20.5,20.5M4.58,19.42C2.68,17.5 1.5,14.9 1.5,12C1.5,9.11 2.68,6.5 4.58,4.58L3.5,3.5C1.34,5.69 0,8.69 0,12C0,15.31 1.34,18.31 3.5,20.5L4.58,19.42Z", Je = "M23.5 17L18.5 22L15 18.5L16.5 17L18.5 19L22 15.5L23.5 17M13.1 19.9C12.7 20 12.4 20 12 20C7.6 20 4 16.4 4 12S7.6 4 12 4 20 7.6 20 12C20 12.4 20 12.7 19.9 13.1C20.6 13.2 21.2 13.4 21.8 13.7C21.9 13.1 22 12.6 22 12C22 6.5 17.5 2 12 2S2 6.5 2 12C2 17.5 6.5 22 12 22C12.6 22 13.2 21.9 13.7 21.8C13.4 21.3 13.2 20.6 13.1 19.9M15.6 14.1L12.5 12.3V7H11V13L14.5 15.1C14.8 14.7 15.2 14.4 15.6 14.1Z", Ye = "M19.8 22.6L17.15 20H6.5Q4.2 20 2.6 18.4T1 14.5Q1 12.58 2.19 11.08 3.38 9.57 5.25 9.15 5.33 8.95 5.4 8.76 5.5 8.57 5.55 8.35L1.4 4.2L2.8 2.8L21.2 21.2M6.5 18H15.15L7.1 9.95Q7.05 10.23 7.03 10.5 7 10.73 7 11H6.5Q5.05 11 4.03 12.03 3 13.05 3 14.5 3 15.95 4.03 17 5.05 18 6.5 18M11.13 14M21.6 18.75L20.15 17.35Q20.58 17 20.79 16.54 21 16.08 21 15.5 21 14.45 20.27 13.73 19.55 13 18.5 13H17V11Q17 8.93 15.54 7.46 14.08 6 12 6 11.33 6 10.7 6.16 10.07 6.33 9.5 6.68L8.05 5.23Q8.93 4.63 9.91 4.31 10.9 4 12 4 14.93 4 16.96 6.04 19 8.07 19 11 20.73 11.2 21.86 12.5 23 13.78 23 15.5 23 16.5 22.63 17.31 22.25 18.15 21.6 18.75M14.83 12.03Z", Xe = "M7,4V6H10V8H7L5,10V13H3V10H1V18H3V15H5V18H8L10,20H18V16H20V19H23V9H20V12H18V8H12V6H15V4H7Z", Ze = "M12 3L2 12H5V20H19V12H22L12 3M11.5 18V14H9L12.5 7V11H15L11.5 18Z", Qe = "M3,6H21V8H3V6M3,11H21V13H3V11M3,16H21V18H3V16Z", $e = "M5 19V5H12V12H19V13C19.7 13 20.37 13.13 21 13.35V9L15 3H5C3.89 3 3 3.89 3 5V19C3 20.1 3.89 21 5 21H13.35C13.13 20.37 13 19.7 13 19H5M14 4.5L19.5 10H14V4.5M23 18V20H20V23H18V20H15V18H18V15H20V18H23Z", et = "M14,3V5H17.59L7.76,14.83L9.17,16.24L19,6.41V10H21V3M19,19H5V5H12V3H5C3.89,3 3,3.9 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V12H19V19Z", tt = "M20.71,7.04C21.1,6.65 21.1,6 20.71,5.63L18.37,3.29C18,2.9 17.35,2.9 16.96,3.29L15.12,5.12L18.87,8.87M3,17.25V21H6.75L17.81,9.93L14.06,6.18L3,17.25Z", nt = "M10,16.5V7.5L16,12M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2Z", rt = "M17.65,6.35C16.2,4.9 14.21,4 12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20C15.73,20 18.84,17.45 19.73,14H17.65C16.83,16.33 14.61,18 12,18A6,6 0 0,1 6,12A6,6 0 0,1 12,6C13.66,6 15.14,6.69 16.22,7.78L13,11H20V4L17.65,6.35Z", it = "M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M9,9H15V15H9", at = "M8.28,5.45L6.5,4.55L7.76,2H16.23L17.5,4.55L15.72,5.44L15,4H9L8.28,5.45M18.62,8H14.09L13.3,5H10.7L9.91,8H5.38L4.1,10.55L5.89,11.44L6.62,10H17.38L18.1,11.45L19.89,10.56L18.62,8M17.77,22H15.7L15.46,21.1L12,15.9L8.53,21.1L8.3,22H6.23L9.12,11H11.19L10.83,12.35L12,14.1L13.16,12.35L12.81,11H14.88L17.77,22M11.4,15L10.5,13.65L9.32,18.13L11.4,15M14.68,18.12L13.5,13.64L12.6,15L14.68,18.12Z", ot = o`
  :host {
    --rk-bg: var(--primary-background-color, #f3f4f6);
    --rk-card: var(--card-background-color, #fff);
    --rk-fg: var(--primary-text-color, #1a1a1a);
    --rk-muted: var(--secondary-text-color, #5f666d);
    --rk-divider: var(--divider-color, #e0e0e0);
    /* Rehlko's blue, the one its buttons use on kohlerhomeenergy.rehlko.com. A theme can
       set --rehlko-accent-color to change it. */
    --rk-accent: var(--rehlko-accent-color, #336ee5);
    --rk-ok: var(--success-color, #1f8a4c);
    --rk-warn: var(--warning-color, #c98a00);
    --rk-bad: var(--error-color, #c0392b);
    --rk-util: var(--info-color, #2f6fb0);
    /* Coloured text is mixed with the text colour, so it stays readable on either theme. */
    --rk-accent-text: color-mix(in srgb, var(--rk-accent) 72%, var(--rk-fg));
    --rk-radius: var(--ha-card-border-radius, 12px);
    --rk-control-radius: 10px;
    display: block;
    height: 100%;
    overflow-y: auto;
    background: var(--rk-bg);
    color: var(--rk-fg);
    font-family: var(--ha-font-family-body, var(--paper-font-body1_-_font-family, Roboto, system-ui, sans-serif));
    -webkit-font-smoothing: antialiased;
  }
  * { box-sizing: border-box; }

  .wrap {
    max-width: 1100px;
    margin: 0 auto;
    padding: 16px;
    padding-bottom: max(24px, env(safe-area-inset-bottom));
  }

  header.bar {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 4px 0 14px;
  }
  header.bar h1 {
    font-size: 22px;
    font-weight: 600;
    margin: 0;
    flex: 1;
    min-width: 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .picker {
    background: var(--rk-card);
    color: var(--rk-fg);
    border: 1px solid var(--rk-divider);
    border-radius: var(--rk-control-radius);
    padding: 8px 10px;
    font: inherit;
    font-size: 14px;
    max-width: 45%;
  }
  .icon-button {
    flex: none;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 40px;
    height: 40px;
    border: 1px solid var(--rk-divider);
    border-radius: var(--rk-control-radius);
    background: var(--rk-card);
    color: var(--rk-muted);
    cursor: pointer;
  }
  .icon-button svg { width: 22px; height: 22px; }
  .icon-button:hover { color: var(--rk-fg); }
  .icon-button.spin svg { animation: spin 0.9s linear infinite; }
  button:disabled { opacity: 0.5; cursor: default; }
  button:focus-visible, a:focus-visible, select:focus-visible, input:focus-visible, textarea:focus-visible {
    outline: 2px solid var(--rk-util);
    outline-offset: 2px;
  }

  .card {
    min-width: 0;
    background: var(--rk-card);
    border: var(--ha-card-border-width, 1px) solid var(--ha-card-border-color, var(--rk-divider));
    border-radius: var(--rk-radius);
    box-shadow: var(--ha-card-box-shadow, none);
    padding: 16px;
  }

  .hero {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1.3fr);
    gap: 16px;
  }
  @media (max-width: 760px) {
    .hero { grid-template-columns: minmax(0, 1fr); }
  }
  :host([narrow]) .hero { grid-template-columns: minmax(0, 1fr); }

  .visual {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 16px;
    min-height: 260px;
    padding: 24px 20px;
  }
  .generator-product {
    width: 100%;
    max-width: 400px;
    margin: 0;
    text-align: center;
  }
  .generator-photo {
    display: block;
    width: 100%;
    height: auto;
    object-fit: contain;
  }
  .generator-product figcaption {
    margin-top: 12px;
    font-size: 12px;
    line-height: 1.4;
    color: var(--rk-muted);
  }
  .status-chip {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-weight: 600;
    font-size: 14px;
    padding: 6px 14px;
    border-radius: 999px;
    background: color-mix(in srgb, var(--chip) 14%, transparent);
    color: color-mix(in srgb, var(--chip) 72%, var(--rk-fg));
  }
  .status-dot {
    flex: none;
    width: 9px;
    height: 9px;
    border-radius: 50%;
    background: var(--chip);
  }
  .status-chip.live .status-dot { animation: pulse 1.6s ease-in-out infinite; }

  /* Utility ── Home ── Generator: the wire from whichever source feeds the home is lit, in
     the one accent colour. The labels say which source it is. */
  .flow {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(14px, 44px) minmax(0, 1fr) minmax(14px, 44px) minmax(0, 1fr);
    align-items: center;
  }
  .node {
    --src: var(--rk-divider);
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 3px;
    min-width: 0;
    padding: 12px 6px;
    border-radius: 12px;
    border: 1px solid var(--rk-divider);
    text-align: center;
    color: var(--rk-muted);
  }
  .node svg { width: 28px; height: 28px; }
  .node .label, .node .value { max-width: 100%; overflow-wrap: break-word; hyphens: auto; }
  .node .label { font-size: 12px; }
  .node .value { font-size: 15px; font-weight: 600; line-height: 1.25; color: var(--rk-fg); }
  .node.utility, .wire.utility, .node.generator, .wire.generator { --src: var(--rk-accent); }
  .node.active {
    border-color: var(--src);
    background: color-mix(in srgb, var(--src) 10%, transparent);
    color: color-mix(in srgb, var(--src) 72%, var(--rk-fg));
  }
  .node.down { border-color: var(--rk-bad); border-style: dashed; }
  .node.down .value { color: color-mix(in srgb, var(--rk-bad) 72%, var(--rk-fg)); }
  .wire {
    height: 3px;
    background: var(--rk-divider);
  }
  .wire.flowing {
    background: repeating-linear-gradient(90deg, var(--src) 0 7px, transparent 7px 12px);
    background-size: 12px 100%;
    animation: flow 0.7s linear infinite;
  }
  .wire.generator.flowing { animation-direction: reverse; }
  @media (max-width: 520px) {
    .flow { grid-template-columns: minmax(0, 1fr) 12px minmax(0, 1fr) 12px minmax(0, 1fr); }
    .node { padding: 10px 4px; }
    .node .value { font-size: 14px; }
  }

  .stat-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(112px, 1fr));
    gap: 10px;
    margin-top: 14px;
  }
  .stat {
    min-width: 0;
    border: 1px solid var(--rk-divider);
    border-radius: 12px;
    padding: 10px 12px;
  }
  .stat.wide { grid-column: span 2; }
  .stat .k { font-size: 11px; color: var(--rk-muted); text-transform: uppercase; letter-spacing: 0.4px; }
  .stat .v { font-size: 18px; font-weight: 600; margin-top: 2px; overflow-wrap: anywhere; }
  .stat.wide .v { font-size: 15px; line-height: 1.6; }
  .stat .u { font-size: 12px; color: var(--rk-muted); font-weight: 400; margin-inline-start: 3px; }

  .tabs {
    display: flex;
    gap: 4px;
    margin: 20px 0 12px;
    overflow-x: auto;
    scrollbar-width: none;
  }
  .tabs::-webkit-scrollbar { display: none; }
  .tabs button {
    flex: none;
    border: none;
    background: transparent;
    color: var(--rk-muted);
    font: inherit;
    font-size: 14px;
    font-weight: 600;
    padding: 9px 14px;
    border-radius: var(--rk-control-radius);
    cursor: pointer;
    white-space: nowrap;
  }
  .tabs button:hover { color: var(--rk-fg); }
  .tabs button[aria-selected="true"] {
    color: var(--rk-accent-text);
    background: color-mix(in srgb, var(--rk-accent) 14%, transparent);
  }

  .section { display: grid; gap: 12px; }
  .grid-2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(260px, 100%), 1fr)); gap: 12px; }

  .list { display: flex; flex-direction: column; }
  .list-item {
    display: flex;
    gap: 12px;
    padding: 11px 2px;
    border-bottom: 1px solid var(--rk-divider);
    align-items: flex-start;
  }
  .list-item:last-child { border-bottom: none; }
  .list-item .when { flex: none; width: 140px; font-size: 12px; color: var(--rk-muted); padding-top: 2px; }
  @media (max-width: 520px) {
    .list-item .when { width: 92px; }
  }
  .list-item .what { flex: 1; min-width: 0; }
  .list-item .what .title { font-weight: 600; font-size: 14px; overflow-wrap: anywhere; }
  .list-item .what .sub { font-size: 12px; color: var(--rk-muted); margin-top: 2px; }
  .sev { flex: none; width: 4px; border-radius: 2px; align-self: stretch; background: var(--rk-divider); }
  .sev.fault, .sev.shutdown { background: var(--rk-bad); }
  .sev.warning { background: var(--rk-warn); }
  .sev.notice, .sev.status { background: var(--rk-util); }
  .more { display: flex; justify-content: center; padding-top: 12px; }

  /* The value keeps at least 28% of the row: a long label wraps instead of squeezing it. */
  .kv { display: grid; grid-template-columns: minmax(0, auto) minmax(28%, 1fr); gap: 8px 16px; }
  .kv .key { color: var(--rk-muted); font-size: 14px; }
  .kv .val { font-size: 14px; font-weight: 500; text-align: end; overflow-wrap: anywhere; }

  /* Load-module and PIM settings: name, value or switch, and an edit button where writable. */
  .params { display: flex; flex-direction: column; gap: 2px; }
  .param { display: flex; align-items: center; gap: 12px; min-height: 34px; }
  .param .key { flex: 1; min-width: 0; color: var(--rk-muted); font-size: 14px; overflow-wrap: anywhere; }
  .param .val { font-size: 14px; font-weight: 500; text-align: end; overflow-wrap: anywhere; }
  .param input[type="checkbox"] { flex: none; width: 18px; height: 18px; accent-color: var(--rk-accent); cursor: pointer; }
  .icon-button.small { width: 32px; height: 32px; border-color: transparent; background: transparent; }
  .icon-button.small svg { width: 18px; height: 18px; }

  h2.card-title { margin: 0 0 12px; font-size: 16px; font-weight: 600; }

  .controls { display: grid; gap: 12px; }
  .btn-row { display: flex; flex-wrap: wrap; gap: 10px; }
  .btn-row.spaced { margin-top: 14px; }
  .btn-row.end { justify-content: flex-end; }
  .action {
    border: 1.5px solid var(--rk-accent);
    border-radius: 12px;
    padding: 10px 16px;
    font: inherit;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: var(--rk-accent);
    color: #fff;
    text-decoration: none;
  }
  .action.ghost { background: transparent; color: var(--rk-accent-text); }
  .action.danger { background: var(--rk-bad); border-color: var(--rk-bad); }
  .action.ghost.danger { background: transparent; color: color-mix(in srgb, var(--rk-bad) 80%, var(--rk-fg)); }
  .action:disabled { opacity: 0.45; cursor: not-allowed; }
  .action svg { flex: none; width: 18px; height: 18px; }

  .field { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
  .field label { font-size: 13px; color: var(--rk-muted); font-weight: 600; }
  .field select, .field input, .field textarea {
    width: 100%;
    background: var(--rk-bg);
    border: 1px solid var(--rk-divider);
    border-radius: var(--rk-control-radius);
    padding: 9px 11px;
    color: var(--rk-fg);
    font: inherit;
    font-size: 14px;
  }
  .field textarea { resize: vertical; min-height: 64px; }
  .toggle { display: flex; align-items: center; gap: 10px; font-size: 14px; cursor: pointer; padding: 4px 0; }
  .toggle input { flex: none; width: 18px; height: 18px; accent-color: var(--rk-accent); }

  .banner {
    display: flex;
    gap: 10px;
    align-items: flex-start;
    padding: 12px 14px;
    border-radius: 12px;
    font-size: 14px;
    line-height: 1.45;
    margin-bottom: 14px;
    --tone: var(--rk-util);
    background: color-mix(in srgb, var(--tone) 14%, transparent);
    color: var(--rk-fg);
  }
  .banner svg { width: 22px; height: 22px; flex: none; color: var(--tone); }
  .banner.bad { --tone: var(--rk-bad); }
  .banner.warn { --tone: var(--rk-warn); }
  .banner.info { --tone: var(--rk-util); }

  .scrim {
    position: fixed;
    inset: 0;
    z-index: 30;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 16px;
    background: rgba(0, 0, 0, 0.45);
  }
  .dialog {
    width: min(420px, 100%);
    background: var(--rk-card);
    color: var(--rk-fg);
    border-radius: 16px;
    padding: 20px;
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.35);
  }
  .dialog h2 { margin: 0 0 8px; font-size: 18px; font-weight: 600; }
  .dialog p { margin: 0 0 20px; font-size: 14px; line-height: 1.5; color: var(--rk-muted); }
  form.dialog { display: grid; gap: 14px; }
  form.dialog h2 { margin: 0; }
  form.dialog .btn-row { margin-top: 6px; }

  .toast {
    position: fixed;
    left: 50%;
    bottom: max(24px, env(safe-area-inset-bottom));
    transform: translateX(-50%);
    max-width: calc(100% - 32px);
    background: #262626;
    color: #fff;
    padding: 11px 18px;
    border-radius: 10px;
    font-size: 14px;
    box-shadow: 0 6px 24px rgba(0, 0, 0, 0.3);
    z-index: 40;
  }
  .toast.err { background: var(--rk-bad); }

  .empty { color: var(--rk-muted); font-size: 14px; line-height: 1.5; padding: 20px 0; text-align: center; }
  .card.empty { padding: 32px 20px; }
  .card.empty p { margin: 0 auto 16px; max-width: 520px; }
  .hint { color: var(--rk-muted); font-size: 13px; line-height: 1.45; margin: 10px 0 0; }
  .muted { color: var(--rk-muted); margin: 0; }
  .pill {
    font-size: 11px;
    font-weight: 500;
    padding: 2px 8px;
    border-radius: 999px;
    background: var(--rk-bg);
    color: var(--rk-muted);
    vertical-align: middle;
  }

  @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.35; } }
  @keyframes flow { to { background-position: 12px 0; } }
  @keyframes spin { to { transform: rotate(360deg); } }
  @media (prefers-reduced-motion: reduce) {
    .status-chip.live .status-dot, .icon-button.spin svg { animation: none; }
    .wire.flowing { animation: none; background: var(--src); }
  }
`, st = "data:image/webp;base64,UklGRvhVAABXRUJQVlA4WAoAAAAQAAAA5wMAcQIAQUxQSMMcAAABGbWNJDV6/8DRf8OejCyi/xNAF3lIRMAh0gnzKf4FwDGMMvNeLmGGPqJMLD3PUdu2DSP/f3d6mSNiAtCBjKEHZXoE4xL75BvkrUqBJNt24zYCuP8NOybxJ+6qxeDhyxETAAu2ldYVJBCO5VVvCaDm1wP/T4Yk2/8XUdXdg/Ue62Pbtm3btm3btm37c65t85w53J1WdRczM+Lx2IqIrDkX1VN172MjAhZtK0EsmEgJjRq9iTW99x0D5fz1n69jQdf9p+v+03X/6br/dN1/Qr0DTCdpkiICJtPZdJqmkwQhAZhMJ0k6TRmnQGkCzAkQQQg+uLpBDs7leeCm8sA7NCUpTmbTJEFgKSVTmwuKWOiV7NM+hEZNkV7VxccE2l6FSedDwO5feXcvT+4MRnw4kc8n8kOdpgTVCUjQ0CcAaetMIg4EkZPJ3mxvf386mSaI6cGZw8O9NE0R987sz2Z77VnH1g/ABBmwPSQEROUDSOZrOQYO7Q4IfEW8uZJVDzyYvSzLNvXW+V2VJrPp/s033/h652+/6fDgzDRJkQGAGLnVe2JyATwBAjGQZyLnwTsfQhXIeUiYIOFAGHyg0FAQPnnPIPwRegDPSCEkPjABBUZyABQQiBAYHhl9khAkKQCmCSSYQDohnCKJ1jwBwlTqIQHGBAiEPkkhaR3bY5hMCWYpwR4SzpCSCVA6AUoifqLawYwhnRFMJwR7CeEeUjIFmqTAkwQ4Tdqec40SgIi/k5RgigzTjueO0rTzOU2xiy+yh8b1gBE/MOaDcf4AtD8xPw1/Ir6IS8qk9SEBhSQtSUQBQCWFB4gJovDilY6ZnS+35Xz5godfOD/a1s7x7jhwmJy7/U3e9PVf78YbLhwm2PV6w490GzE9YNufVjIQMF8jYEImBmj14RE8SwjiqgaJ6NXqmt02ddX2u16LuZtD+Opp3L0rcNtcyS/XDz38khff+9LjkmjX23bj67/Z277pzd4FRhgomZlCdf/Ri57/kqP7tsQ7GU1ufL13e++7soZhEGUOTb147tOf8cKry3q3ooNb3/eD72gYhlZmv1m8/IlPeNa88LsRTV/3w9/39sAw0DIDzV/2nMc/4SVV2HXo5vf+2DfyDAMvcyhf/Lj/feY99e5C6et92odWDMMwc7151r/858uz3WTK742+7O0JBmWm1Qv/6W9eWu8cFm/4Je/IMDgzw+JRf/qfq52iP93+BR9AMEwzu2f/1l8e7wx07mM/N8BwzeCe/YMHO0Kpt/vWCoZthvwTbsIdgC592XvD4M1w+HZv0fuf5J2+2cEQznDHG077nfY/86N4KH/Nxt7rzvqcbvq2CQznPL2U9je9/neHYf3NWYe9fTF9m+8gGNYZAvX08q0MQztx4/qY3vC7hvcFADa+h2/Xfx/BEE/hqOndWc9v8jDIMzQPUs/S+78JDPTEm5dxv+q+mmGoZ3jgqFfpIxoY7hlesOrTN8l+1oC/BqifkPcnvfkMhnyG9ZP7k97BD/vEz39Bb77R4m0Yhn0O/7fpzRdHw8DPsPy3nhxIT28d/Imf+dyefN9kCoM/uz/tR9VlD4M/wz3/xX1Ie+kIQK//RUkvvo0uGQFo8kVv3Id0FmEE4Ju/fNKDNIMxgJJPet0+HCzBKMC3fWYPEuIoQPhJN47k/yAlvsHbwEjOhx+BY/nqg8/235kdCz6v80a9R4t6JKAzb9l79PjveyjwGECTd+i951Hrn/2A7/nfOY8AG96i/35fQs/70Y/74zFgdece9B9zOgrctbyjD5/QufSL7zUG7Gd2qQffTPetnz4ZBQzv7EEEfYdkHHhC50z/Uf17FYwC3IMX2ff7sYNxQPRfsYPvvRPGAebeo1veDEeCZdt/L5qdjATLSx7Xf2eWR4FU87gveqAHA6Lhn5aP+e3P+vDH9F/3oxFgy/qLv/wvMxjB13DrG/l+jIlo+KfZR/Xj/wcehv8VJJ/xbj35BNIIkD340NH8LbMXkj4k70cA8k8O4/ian/wPI7ka3uI7b+pDKgWAkotf95uXAEbx5+rTj/xsHMcJJp+z34MZCtZ1u7n/CAPuwTv3AoFqyrF87VwP3s1YIIjRcWO5YB7L1b3Y+YRzTwYFg29MV4/jD+IFeA0yXhggfA2ytUAAex7Nr7Kvda6mPnyu/oCARnMRRnN1MpoPlYhH8vdJg+fx/HfvY7kgeA0yLhB01Ifvn8ScQqLcbx8E85KNgnhbysWGOZw61AfmcXgFgtEXMF93XSA3QrpgyZOTzevWbxQZYyWh3FE++UPgPD5noWB+C8qNgLlRBtk+KuTwunlsBHNqEd4ohwWC0be4+bpu4SYMsrvmRDrsdA3LJBOkr7vu5rCADvt5XL2f++0pH3xi57DZ8SWL375w7re3c3i7rIXnmDgogN08Di+1aSDOgsHF9CQTZr6um1y2x9WHu8v2uPqDcjhsX1/j6idZMz+Pqydx8H393/e703Gxc7HMMr8958klVkejzG8vl+37fi9+HlcvnDdz87j6AnreO+cnWTf/XKuH1xkB8/icpUWDc2HncfXHVXtcfdjEzNddDwfmYsPgzbFB1kysbt/vRxhkwahFKE8i2yCgDgefYN6sUB68Eu4YUNso2xcN6B1ZnSGkx+GZuSiUU/hh5377grm4IX0Phoybgnp8jplX4Tx/Jo2y9z6S1cGhRaM43b5ogkwyuAjlOgjnvi7Q3/owc7+9YA4XBgh1vz3kFQPmRuK8mZvvryD0OPa8DhbIjSBHj7bVwcJ5CeXvcYYe4YJ5FbG6eeMPyqvIEQYZl0K5MDvmvMqGud8+YR6HVyiPq5cfwcwnmpUyyuarEqdbd11Kl7DPsWB+SyQb6QbktIRJxolyv72Er67wMcpEcTpYBHNYQosKc2LgGJrc3G8vxc7hZZCJIF4HBz+fN57zXFHO8+Qov1gKaZIJSW63HjPjJMHQ894hv1aSctE+b3woo2xdN0EAluDmcJBR9pnShHItFFwrubnfXiiHJVEOB4FAD6qdzwaOoWmSaUmgd0T5s1AADzJeKI/PkcJ5cr+lr+vm5CqUDfOAW8F86C2kn2O93G9fDqvz25dR5uoSyq+lpVC+r1gJF7R+eymYC+lRC+UPQYCOJlUwOi6Yx9WX0iJMQZ4c5FSEc9jN56Xj3G8vlIsglMNhK7Ms2JCBoYd5sx4fi9PlyRXM/faHhEnG4wyGwGnp5ZzMbp9Tk4zsHJaCuVHsPE9uCZgXUD70wgb6KZZyWpxOlCYn5QL9psjo9kUjpAcbcj5vPOZ5cm4OH03CTidklDUTp/PbhzvS4UnGB+ZGCUbHB+bz0h2TzAiyeZ3fnnK4yUtpwTzk/A5zUZzOb5/sfN546fF3ewf6vPF+DkM+9EQwh48r2s/lcswyIQSMvC6rGDrMeVy9m+8H/HA6uMyyeemEANp6pBsIjEkmFjffRwVQ8lp09+3vmoT5tee2yObmsGyUwyI9Zg4wjN8ZBGSEgMO/kN46QqFPRoI/7FaaQ1DkEhoDKElriPwk4BjGaUY5tY8JAiSAgGMAiXT1jh9yItbS/Hm3zsbo8u0CmACgkK0nT2zeAYf/DtmKQhC2gK2QdnKwtP3HDzk3NltwApyIHbBYuF2AXnD0fslYrEaQswEs9yLshaaV7P7zHW4di+0ZkQH0IlCTRUo4wQ89/iOH/iKpBYUKVaQPUrYpJGRVnJ5w+c1w2M+00Y/pASMbp5QN+Mz+/SPPDPokpQVHBTJ2QE1ZAwu/hN0Lpm+IY64JMohFJBiB9QdZzRUwyuqoODfsi9TDUw4XIjEQoyonUwB097sejrc/k0M29XISgLUPhCATahM9Z/k+yYBPpfzvn0ZNqiggm4MLFtWqZPUf73Anjrs/exeRP2oHpK0KhiIxxEN3f+zBiFuRCSSM3Al1WNSEbU1Pde+Oo+9rbFRMYFaHrHzQ2INc/fO7Dfeq47/+MIIExlaCSpsuANjuXFM97qNng72QZlyTpmjtRB4ZtS/0RHqPZKin1AI99ZPS628EUT1+JHagivt7D3CUFSG9rJcegZRiTxiykW1dyB6ejcF/HuKFQrA3sa1/kNJBnsAn0BOr9BLQfjDbChU7+HtmOMx/kHvkDD6Ij5obCWGazfdglOU36n1PrKpgE23ofhriKwHuHbB5wtU5RbNe0FDTiAqHd8K+WR5eGeYMoHdiCIT18XScVafXdR9e2ROBarsSLFQPJMm4K0JIb78BFSIYwZFCnOZle+Pw33WLDI7kmkGtWjvm9Xpw3xWEpFcqfG7eeaKTQTMdwdCuAkr7ZZVehN1KB1AOG9hWiVxz3z4O76JPVi/yaE4gtH+8XA3tFTZp/z27Iyw6OEBHk4F91Ux6BlTeJswZig7znFwd7Q3rn3oG0C+q8BmEtoUKHHiZDesq3z+Zt20jv4BnG3HCvcmQvuIg1D2lAkRk5YUhdJoB6vsOBvQPP9Av6l+EmHVGucTHm8lgTlD/V89se6GNlNQyA0uNbU5Hs2QgJ6B/P+i3uhBt4DGyBpdH+wM5wdEfY99s/eC7QHs3SsfaHZ6X6SBOsPzJSU89lINa6HJojB/kAsou3DPFAZxg+3P7vfYIHqK9jmQZtU3x4D4O4Muvnu0jizdKJaQ28kMaYwdXysG7Qlj9/LWl3xjtiUDb1KZw797ATfzgTx324ILCtsMtfGOUwQiQPzhoP1/P9KRf7qtulZ7rxg2AVVbUKYRwgq+6dLheeP6nj+/HCe4TGQOoBLiXD9UqCPO7/+rcBPuQpIHxz78DdygqXMsfGo5fUsdMnkPtt/N8dby970WXZ2mCorf1mkprIt6oUqosqykSN+BWKPoRM/u8zhbl/Di7mmXLBvemBxf2D2aTBPtRJySocmKRGnN/Qu/vHVaLgOo15HxeVptitSiPs9rR9GBy4cLhpcMz5xpPLUsney5M6OAFGvpIWeXH9srecBoPNM5XTbbOr2RZ5pgn+9NzF2aXz+6fn832EkwRE0iI1F1rZdafd+3NmjgCrayGFPQgJUPmqCEQe6ry8kq2ubrJtlWO+wd7N5w5f3nvcD+ZpCkkiMjysXJERNGdmEWqLxkhYit2wNzqWWgM1/y9+4NksN/UmyyfF4tVsSyL3DkZBjCn02mSJKpDKbuEERJAoWjdRujFFMafr1cVdjvlEmmy4wHQRnQKDnXhtsV2UVxd5YuyrL0PRBSYmVjYGZEAMopuxSjKaQ2IT7+yOP0RvEGhj1eP1yQ9wMOdioGdd7VfF6srm/l6u2mqxocQiJiJhR205YBYsew+Alf0IgSCSvUzI6DGGrRV+rtV5dy9+zisgQozeQpVPs+XV/NFvsld6bwPJCFFwoo1cNA1MQMBW90J1ChZCIA+tsUOXqBygLVPHBmp8XoxG8ACAgkr+bZcFMtFPs+326Z2gYjisKLqA5KgwmDohUTdm7Sm1UOfs/gGMIY3KL5nI2F4QffBIKVSDZwqV+T1crNcbI/zvHCNp8CBicmAFBJwYjKocmDYKSl7lFKr7bAjMGqsYctUfFNsYs/g9G+UMJGvXV1urxTHi+2iLErvRLSvEYXUkIEsXAEmkGUjoAKqJuWCumIyio60a7CRUPAemX5hsQNeLSdD0FReoODcdrO5Usznxboqau/ETD13iQiYwBo0RGDFkCpn6LXdbnEhRGWHQgKaIQTbwzn9XSEfJclwE+1zKOr1uri6Xa7yrCxr5wOpgEABChHosmoaz4AVVZ/QK5JHFMGUHYoRzFddiG85OqioRYVDSrQffFPU201xZbtY5cu6qkMgUqBC6gZch1EDaL1RVkgANnKiM3Qb8e4ueGLvALtfBCziVTYbPoL90ARXu01WHK+K401V1LWM9knBSgRRRAKMgUMEU5QEcxtwJxzhHWr0YNihoYp/cSxz4SjFQSLUZwqhrKrjdXGc5VlVFr5xPgRiA1NkfVZE0CHaZ1D1iR0YLR3Y7AEcAZXdjdGoSX/FqL529SUjiD/pOBxE+hCaOivyVZEtqiyri9I5R0yR0YIRE4DIqWgfCBSsKDslQZdD3kUxxRg3SKGVhp34VlF/wXycTfE0H+iTL121ddt5uV4Uq00tHnwlA1OM4cKJ7rG3BEKvpDgmto6tXSKgsssyipz6ao2GoP7p2NnpmhjYBV+HalMt58V8XW6qqg7ei2k8Y5igNTaqgFGTkVPtV9ckXQDbbifGFeM3RPY75EGgPqi8aBDl0R6ekh9pb+plVh1n22WZb5umCuLuujFaMGbmCSLDBRLgYcAJg64JWwesHOjhAu/EmGJEBidTRr59vKaqpqfUQB+IfF7UyyI/LraLqtg2TRMokBgvROfuOgQCQg8KViJS2eqG2xFTdmtGITXUSCWbbYCFI9c43HM6JJZEjWvyploWm3m+XlfbyjUhEBNR7LabjSd6ByCoG67I3IlBZfdnRPOnwaLhiJqsxlE+cHiqUzFRqL0rm/WiXCzLZV4VTjzQzkSRUEAQGOFAZKSgyJStnb4K2fpHPNrfoVXGg3j2DvQGFm7wlTI9dc3hcSDyYZs1i2Ux3xTrui6dd/JxdlawAhQPBcyaAJhVTvoAIqd30OojkMImpJw+GIWMAw6A1Z5U+/H37J2KAn1g5rqu15tyuWkn8bK6qrz3JMcLZN12I+gGKSAshPvA+kAA7Jyp7wAlDKciRjQXtj1AAPXH2E8vgb53Rd1kZT4v1stys3FVE8h6QQQQc2TYAJ2eiBOSwZA2kGgPjHLIpyhQwcgOum3jyAUK+GE3OU3Ux9T4UIViVa2Oi/UmMLg6hBAUpNgTeQzMrAcOoMN+EFLZGeWEndHUFHXDEYZTFqswIeIDmi2IzSbmXz7b9QN9YgrU5G59XKxXZemc5+nh5Nyl/QsX9w5mzMwnuPsGYpvKGdJ2wNRHAIQjoHIqY2PwbwhGlEuHxsXCnfzqAe7mgb5rtptqtS0XZblxHvjwwt75iwfn92dnJuk0TRIEZEStMcBEjRhETtkpqe0ikGLUxLHxwmmR0V53jDoZULVBfrDZgYkFEVW121bVosjmRbaqqsr7g/3L+wcXZvuHk2maICBIVEHRMAD1QMGuSTggpLIzcsg2nDACRzDlNMsYTYgGirKtqgaH4O87s7t+mEMItXebKrtarOblpmhKF3wg47UvCSJipIHIDyACI4s2AtJONRZW1wXVcoTevm50mU08BbNuuAjYoa2h1QfWV3ZKG2YmCtS4zbJaLfNFXq3rphKgIm67RefxQHPCojEwxuyAQeWUC10BhWOIckpmNGwjQNJFwQAoVbveS+rkhZ6ozJv1pppv8uW23NZNHTyRNT8feeIVjBl60UridozKDgBaA+QIpHRClNM+o50yGiOrgafyiCH/5w++YSeL84G9c0XZbLJ8nmfLKs9d48j4DRpBBFWACew5epUz7IQDqJqEOjS2MaULqAwMjMZDOhhtnCj0bZu+59kfMdmZogESfw68zudFdlysszqvvPeB9M9UCNpyQLF7b2RCCkMMVYSM5IRezeZJLwYLWFFoYiymN4Cqgeq2LIam7u6b3gZ3mDEDXWNP9brazPPlsszypqrl71SYdCxAHX5d2um5GTAcAO6GKCcYMAwfjAao6OdumYWd0WZZrGDzbx96cZeIBbiV7Gtfrcsqy9o4PyvrwnsnQgHqgCeRYMDQg7YDTdpOERh23UBlEGG1MlIRfzo1YqQXP+/D9/o+yAcKoSpDtXXlIm9Wq7rYNE3tzRcoi+HCyV4MoXOgatLl1MEZLlhl9ahO0fDDdoLN5swg14Duv868D/YurDA5T40LRdbkx3m5Wtdl5ZwLFAIRE5A5SCA71gddEwG3UuGKlipHKL3oACqdEG4QYhQpRLs60TtU41f3jcpHv9Nl7L84gJiIQtU061W9mZdVlruy8s6pn6gYo//4QIFA+QKWHrQdABsygifKrhuIMAxGjB28EAq0WjcKySgEI7z0mR8z6SNEEQF+qDZ1nW3rbF0X66opKu9khM8k0ENhiCwLBPHhgtCrnJDtESmpCYCtyXnuhiiDFiMAKk3nITOA/AD7u/H9036I8MXLIEKd+2aZ1+tFna/runLek3lDHTq+5MWwU5Cia4qgimEX0UtijGLK4MaosCaSVX1CZ6H4pzd5u+TV99Pr5Fxo8jpfbtv4flu4qg7Bize0kQklEQ9AewDxmkDUZEpgVt8SxHFF1TTU4Yo5ckA7Ee2XzCik2MTzv37rd53gq0lAYXEv3bssc5t5VS3yJi8bVwcfggoDdETPELEFaQds5oSdqkkQCgdAkMoJvSrHXVCEYfBjjHuAHTZKwYxw5W8vf8Q5fHUW4JMrarcu6s2yKtZFXZTOeh+6MSXP0CEIiOhBkJIMhg9GjuW3wMAoXTFTEUgZIhmlQLQ7rOiARle5JoC2//XSD33L6auN+B6AgxPx/TavV6tms6qrvPaNCvBP8CpVVQ5UDmwXTAkKQOQmA0zYOm7uBCMMwyej6B1WwiAW29ossnvef5z9oNfbw1fdOIDIOXKVL1ZFNd9UWdZUpQ/iVjpHwgCI1QeWAxCx09Kuqc2ZNZl2bMDIwAoqqOxQroy0+YlfMGn7pMfuv/2bX5omaQqv/NWxQBT2HPLc5cdltciqIm/qOjhHgeScvKE36jPCfYjmhGQANqSwkzm7JmHXsZxBAy+jLCd7IYhua/YmNXzOXviU++DswYVLt9xw89lpgq9E1anezQxUu2azrfNVnS+rOquaqgreyZk7AplTSBKflwdDD5IiUtcEHMvZdq+Y4cJQulKpiBC9lMzex4CEohoKm/WqXC3mWbF38x233XLpwmECgK/QCJ8D1aVv8sqt1s1mWRdZ6erG+Ld5OkT3DLomUR1oUj60EtgohwxAZlhv6K0jZ+gOKUMzY6xXcdsTia59gLHtZLp3IjPKKW4CDj5fJOlkdnjh1rte77aLh/spPoIBPntPrglNVpWLdZUt66JwvvEUgjzeWHwP1G3mjsG0Y5DSthM7QCAxMtJwwRFoUye1ywzjYM3cBQFkLzc7JVsdEmXsAHiNk2u5ZHpw9tJtd91558W9Saf5Am6PgwJTU7l8UZaLTbXJm7L0TaP/O1wwMKVLTSBzxhKTDKByhh0wdLATNXU/yzC4s+ioapEftVJdkBnbcvrKi4zQLij20ha9dNMdd91x7vxBmiaiKDXr3G2zOl+WVZY3ZeGdC2w82CrtInhi2MVzEalzhhO6plg54O6AMrxzp+0MRncn4Qiy0WkTinVTIWxOkmQ23d+f7J/ZTwH8drGtgw9E8QCfwK4pAipg7ED5IE9GBywx9IYDBhh2Gf+PDiy7sF4TKV+M2JmjQTSCuQCKfSKj7tTWCAFiU3hg6IEiiKJI6FuSOQYVoMjzoI6eH5H4foyoz8gZKEBM2HZmMLo1MCAAGxdsUPUpO5kCVP4DM+hjgJgeInZKgjhMiORMvY0mXfGDYdxgtk1Vr2dq00QMgMzYXrnRuHojq2u2+oDW2P7rIwCOOKAdAmmnHNC5VopNyB0BhTuME0YZZjA6vExzu8jOrj7aCzCSaMiWWBOLQzByEVQRErnNATKLQxY5YBMzIhSdjGAYbVh1WNHZha1SayhhkGmRaF0QC3JLIodsHgILCRyR0g64A5iYLpxgcMAwHrHuwawu7HqeTmCIdelmlIvhKSq9coR1TaztkNRgQekjHgCfCFJGK2bWXdqejxddXS0iaSxqJRaWZgxaH6mpI5BwBzwZ1Zg5WlSNHxg1ACCrQvJB+3jAYep1TdwZQRjGP2aOYYLWMKCBNNLUGGd0QxLu/GTvyMhsDikYQFenwASjOMEnwQ+GMZUxghQcmdXvMk4Ygxm7Df8p56//fPqi6/zTdf7pOv8EAFZQOCAOOQAAcKkBnQEq6ANyAj49Ho5FIiGjIqLw6PBgB4lpbtzYusogf6FVNkoZyeU923sx/Q/FcScReXP+v54to/1fsE8r1O1zNvPnGMt2y/6uWBl5a/N2u3qo/oHRbactvTv+Iyc7qV+Lfmy/m/+B4o6x7CH834I/zr9I/t/zW/unzN/w/uH9G/l9qBfmX9N/2X9v/bXkbN3/5HoU+3P2r/Yf4/9svgQnYfX2oF+sv+S9hP+L/rP0z9Hn8H/wv2j+Ab+Y/1P/xf1j8kvqK/zf/N/uv2G/3X//+N/1r/5P9V+4n0I/yr+q/6D+1fvd/d//////vH9ef7fexV+lP/PFAC94XvC94XvC94XvC94XvC94XvC94XvC94XvC94XvC94VNEnZ8Z33dXugNHFLc2H3CEHZPU+wAWj0CZgqMXBDv6VUCh9FKEisa8gbyKdJkJFFkJPWzmXR1f2r2r5FOkyK+73vIN/NavavmsrhwMM3E/vC94XvC932AMbV5f/LEEnOOnW/+ZD+rcHcQL1UaOVBIrhfY/d6154g2KMCDxbUPcW2s4cXcSbd11PFbpSdxmu0mJi7WGQkS9JORoDDRv5RphJpOob0IHtDLs4rCFQpzKR8xrmTwziQjwoZiiCxUwHrNthtsNs3S07XexRWTl/p4k4FzfFl+BDoJ8wYfhjLTBYTBYkxvTEashalyBlx2TWkLD4Rl8VVg2AYSL4rLOBBT3QT9z9HhS1xmP8CepwyklQIlWHqnJWA0f2kVhe3iDUzslLKFNS+OjZRmd9mY/+n5/20p+nF6rDw/1WW3/orQveF7wvG+xTpxh0v/9U+4m1iKdbOO9+1llYnc+C2RK9R8NPV1fIjkgMvT1tHwtudveQBRVYa/Tzigvf22r/Ani+HOz54gpapNJLJwPiiGwCfRg7ji3Ez3VVF3gGOrLWSkmd5C2gv/PLO9MQthHDHu5ZEKfKdnAXsByC5mwrN/a2qsgF7wveF4Q8uxEUI+YSiSH0MPYD9drbAn3QbAa+ymr6DdITiGNPeVd9xWMAhO5d080xvRviAwb2cTFO4GC/lLnFbHOMFGVfycFRPWsr0cn4N+JrKo/xpVXKz6KgMQrSN0h0hva/rXI1kIv6fKvO1Rz0g1kPatDBMzeaidve0pUQ4E5rqeIYOdMJoQgboeZANz6s/Vn6s91xkkqctXgZm5yfX3Aa81Ze9CVqCyklmlsCniipVWeRVH+04iYy7Nvxp4BfgCq+QzdHMQKbLHzlxjDL/7pl5ZUTCrJ1Hn8S1kiG6g6dVkFxehNUH5cZtAG7PRNEKjLq6u0G/AnmAPLqJm3mKuwysNbqT893spJs7X3NIE4lTjTN8CQK3+SAHdIziWNDkXGIdpmD+ZT4L23tfS6xOTl02MnVBh/MmmmRt3ikSVHUy7OiDC13l6gyUsEPt+/9Jo4HQ9fJEGH1QOmqOFoEbAK0nyG9ReyFMbYbbDY6gF65+iOWjxTFc7XPfajZm+fe/Z/yBifM+3UFDWS16/nbzrCfBTU7WB1FI/R3Y73sJBhryD27HOXjDmMtXmRiF+9FX1TWzGQPbCH8M7vxQQX3D2wnM6o/yiwLmaijnitLxJUmM6JHCvOETK/hP/TJfh/0mfTC5jN3D6WE0Xuq0pxRmnrRa8lC94XvC8Mqh784BPkXBs6ko17orJqPjSdMuWHTVIEeAHY9aNDGG70Hcu+aOEQkqEDazbxQ7yQCwbpKDSGWeVn+gHeDeLx2Ok9RIFdYc2eyh0eeS4FjtaBdRbZFFb9t6H6qCzF2fmQeCBYsJRVJJ/+duSTf3am7/xSQ/hpubGE/cSUXgcVJ+/Vn6s/VGhzi0lV5yBl6GBt595HT/ia3ICyVd0iiF0GtK5xu3COOJVQkpdDHWP3CuwAJbW6uNFRzqIPLFf8gStsllAOf+Yr8B0XgGDNjRC2irpQRts68pq8gSIUC23NKuiomIB6GbQsGxt9eqXfgBqkcswfbFUcr0LSBFMZ5+9hfRWEbXwfGvKjrG1DHVyy49FrVmFC+rZJAL3he8Lw8gBpjhPCzdQUPXSjrIxuoU2i/f/vKTd4Smiyz+ZknaXIrY3iy/cf5OEo9G2G2w2148DiICIWRR+VdLIJGpg7A5nIvhP56Fu9ckvJRaSx7z8G4H7L98pvOWZgPgT32oFqWqJ6GbQy2OowHFMeQFoRUx0kyrlSOQCo3RE1F/wJrcfSzfFJr18+6eBtON9UTQ37dM22GzPvaVp/eF7wvd8nlZzjtd+QN0/a/2yMGZflrno9Da4biLp4G006bX99osfBAF7wvdSDOTuFVYPz0NNfNpiy/feF7g94LPbWAiXUnpUx79Ezd6Zgqk1TVTloBrrTLMYk02xAPQDXgxPQzaCRqqAehm0W7IEOg1yey94XvC9wb/bCx3kFr/a3M6HsLVmZoHv2S6tIE3iwjef/LE+vym+ID/bR8qM2nWfvEBDNoJDvq7L8NkT3+EMbYbbDbMvGS3hjfTt3QrB32rBkjKc3wbLbbhvmKN9T6it7vh/Jmb4bq38fMOajjMVt/efVn/fyaV0L3he8Kd2ChdGyn+A/lMjDu7kQacEhAFWKGf2YUiD3aREKnt79Uk3eEpStK92sdZA5JqcDHTNthtsNxdytP7wveF7vkryV0iJB/FUecltf+A+awPrePNSBe6y30bBpRgIXkNWJTtWCJdhE8M6mMxRtjzUDTUUOE0jCMQUxthtsNjnMYc0dm0Rxc+5iyNvpS77xaSSDX3fzOlmfJUkcWw0CB2cEpY909C4eLEbYVgBHnV1oIt+oaDSh0Gw22G2wuiBeCeznjK9F2CuDN0ni1DFpVQqQuc86pv/f7S46NqveUqmZRIykACzYMnglLJNjGrkkAveF7wvDu6SEuGrh7dkUdeZOHSpQ+cVZxRecB4EtZIxRtFx6JHkse833dnjTIzDNoZtOM5K16j4/Vn6s/Oez+6PBiFnfXrnSI1PERJ3+wr/W7q2ARozDOuytNe9lBN4XdNGFwYp2mbaAh4w/soh0p7+dExthtsNsy+7Lj0SEdh6k0shjZbXXh2ZTOCk2iTUMzdcTwS85j7O1XvKVKVk1fMD9939E2e7po6CmLL994XuD58wNfaJ/Ry2RZSvhJtRT5eRiNE/HmzCaBzN15LyWPFRsrfwZ89DNY/WOZJ0xjfvvDAzdiEyCNoZtDNnnRkyaKJblBGUOHqBBXI0Xbvl03etp+ixuoUtMkvHuG14jgmb5lCKDwC9J4sRrR3+6KNllJca9wo5KGbQzaGWg7m2kqiyHdVrI+t2dSNFACj2aT1uUpvPUQBzXlD0YpeSi0fKe1ZW9yTs7Xot6+ibBH9eQegRk5KXj5ffeFPNliOi67EbkxjOMPOmTaEANhzMfEBiQKYwi9H6nmzuDqGCbrknTGJGy4NlxPBKWMi6ZX+ynbl49Wd/vC94Xu+SoBPvtY7ljFyiXW9GUo2VJrHz/7G+hrSvjtfPPr87ytpkv56sUzhoz3iOCUse6egW2rurO/3he8Lxj+RSfPBFP1J7VToQJh+k9ovA0jsxyPQssZ5i7xT0HWHsIwyeEOadM0Yq+cZFHuG14jhDxisG5O20nE9DNnspjpNd3G3DBfoTddZ7gQcCS00alPWCpKErTrYBtWVv4Smb4rzqdqytNe9lBL21Tifn6667Z3k3GLL58ZF4ylmP3Poq5b7uuQVRilooR5LImt1qVNl0TvcUm65RI2XGkgdL6MYkD1Mwu0hA9rBkqOk4uUaCOh2xa4Wx4dpf2OSYkMyWqO7sWHqUtArIIJvEK5JAL3he74qO/Sop5MhvMv6qsqTliLIiOiALlLMDPglG16TMxRKeEF7hg1a09vNGA1hYkon0pUBPq6okTaet02Cz1tggDWO+dRDMVW0uE4U4oOt7BlmDAXLwHaBI7wrHxuCif3he8LxvpRHUOwJJWgT3d1m4KrbCTuH1mMb3DFL6cSngmcLul/z7HnXhPV8XEIxCL4OtW6yw6xJzRT5iAEPx0L7sHF3DYWpwKf7RwCc0zRJ+ddMaezvwLiIJrirvKg2R2O1n6s/Vnv99syeUCZNTnUpTyb8UuYq/N3+my4MUvsYdxxR5v+GkzOS5b3R2C7xkwvWt2mDyBa2QldTELOOojYjteMRUpJ/Wa/1fmcAC450GebH7gNXgUPyxQGfC8jlTKFr7pdMbi0/LNqvomw2zK3nK0V+GT7mCCYGaPDVFYHWEijEj0G421Ms1x8noZ4TGD4xoS024sPijKb9/r9/6C42uqRB3eXRfCKjuB9faGeIjZ+lgCRH48K1yg+JHgLpasmtaiz2BNdkiEh/vn/dOKWGzEl49wxS8e5TNthe6a2lEVSNg4Aa41KK0GJCSPSXa76HA5+ZiQ/BWtD2u5Hd+MpCm+QwZW9BLmd9vbM473jpucqO5hE8y17tLP2jUWfoPKOFfLPrZ15Rgdm1XvKTXr3lJr17ywEM2hmvdvTu17vKDulJTNuVzjNSjhjG+p9PvZVmHnRil9i8osv33he8L3fvYOapm2gIL5UXHosKdqvomvnP3lJu9HeJ6Ga6AD+/cCAAAAABLy+jTYTnbeT8ZAmtvGmx4HdlBI5uQ+CUFjHw8rNcxijfXOJO1oFJnSeCGfZ4/To1nqJ3ycGchmEWGAXE/p+AUZZgvfp5bu1rD7Ecw2TqVZPvDbaEV+J4E6SvY20Er8djbeD5RjgQ7oBEfgwm3IkYHhFIIJ+7Gl6L3MOqOmkyRoqKlu0CCxU+UP+4NTI9r6gJEbg6Tj1vO5lqpOAqY5mvelIwt74YvLbyo9hkrVcsuZcbVO8zGrxIdexSbZrPEZke8fE9UQ9hq7fKz5ibKiBwSRj/iwLv0Dpk3zacwd/USRMuHhxtV4z5fhom1K/Wj17g/cc62VUvV3eCAe6O6E34C7lJXW+l7sZO1T4zEqBN9dNAoFk/K+Brfw/3nFMvCjbB30mfs4x9XlaE2bfK/kHKq45HEeJzUjKJvkXqpOrbsJIjRnpWlLGhQ8cYUMXi0i5rNnBDxf+nikhAKwigaw9clOkASfgVocjD16k4tKkxwF3U548NJscnWyLjW9BT3dlMiWZFJKEf8D70iRRB8rmZm1tDDLjURUWgGL0cuh974sIRHv2xHDqXAQ3VHZwiGs1rqAO1V5ts9udk+bZ+BBKQYGCvQtYmfTkTERsXXRacIMIt4aoid6U/pP+S44yMtvkP5mutyNsNEpivL+ObhZdYR/UaWAGiIVdhbeRQYuE9VkIMoVkaNQ1a8ZzwThKo0Z6cyrF47NTsjdi/ZW9BDfCqAw0RQS1wxLedcUpDtaNR6Tu/1q5SELUFbvgR1ivFY/Py6WW02IZphQ5ih3vc69C9VlCWU5yhOLVcERlfUaO5bW53NceE8oCRaUaBPhqgEl31lBfN68PfnS8uVCMXsKFsl8UGzbm7vxxgh4v/TxSQarZzAtuq15+U2sjWG1/HbMnkclCG303HBRaHX4LF78kl/u1mlLQYj2CtIjtFVY90y9WmPlmKQ1VBtojIisl6zAGePJmoaVnCxyQdxFs157RQ/+yO99i4Eculwcx0dcMvcEkugBYW8NiHRSqoSTAx8dZAjphrkOGzPf9m7+0SCuoUF2qlrShajLe71roIjaszaXZaQagrRs4MoWMDbZ8k5aTpUzAGICN3K6+9hmMK8S5O8f7uAoKa7JwMawDkxLDVhsk9KhBTBSRf9+WEZonib5s1wjNeGaJqNHQkDTKAnM90dwPAP7Qh/edmm2OAe5hxpCK4763AEGkb3tQyVkPuwaxP2fBuYhjv0pAhCtMC/Bg3yJqrcCH2QMXGOllWeIeWe9f8s5QbqCNeVcWJ1BkV0qSBAi1pehtjuR0PPVMDEKgb8DorZL1h5vHq2P1ltqJLWxGuKfO3uMSOa56WABacVblYIc687yQ/Nn9i/Ecss7WmjLqfWe0+mYKcHL4RyTh9C5RUcVbze2qJpBtrhg8gyyu7+Crv6JczJ9PRorayJhSn/fLGy9WkcBR5uOZQ4Yo4E+wcpqQy0DCPvD7AqyFUwwGeyH+80BLct/H57jutntAY9rvfDbGHPyPAsEIMQjkdS+DJ4Asbziix9hLk8IWHjDuSJ/iARFJaWk28HCChrA0fi5g82ZA5/dzSVjtivvZUu+xzDRL30g1Vef0Hu+MxNT3GphBY9Tj55FGGjusxNuCyhNBKeDcD0f2gj//Ewn0Lb5U3TmN246xq2dHCPX/5YWbbt5Ux/ZzRfaDieqSCcfxla6brJsAgdx7w46Uy4NlukCJTseGK0DU1GX0pP+Mz3s+iDWw9Ep5kACozortiLkm/uoDUORn/Jc5I0UwP84bvEHBhelGUpPSMLekM/mQbXf4CXr0ELxiuuWACeY6BsMbjsXm22reXsXVG1FXs7MH0d0T0jAsWtb3y5VFK0dVTnmvtpV4TXOhZexXbteuQSuxIRioIYX3YDzbaUYWomoZKvjran8Ye6BHEo4Ek4YHdB9OfjaNjYIQRy9G6gTssBdOOW42jta35nleVc0N93ZRZBRH1tdTUbvGBvPt6MuQOOH24WTwVeoHhQFGnI7qS5/5mrO1H4JeNBoyOFkfM75YD8U0+iWmDdQAP0/u5Mr/grvFNBzvM/hoc2Z+0uhGTUM39n8zvhBeJAjsP6mQptygNdmqTks4Ih7KqzrnA/dpB62hiaD+ycxfCWDKA4KTlYuICk2vQFBVbOISS7yRY/UWubuL/SeMWQFbRgtQBNsfNeqT4ZIlbmFl37KJZfVOm7mW3yQdO0RA3VNg+bw2JpTtnYcrl3x8lb7gzH3740zmCBMUbVWvVz3yUbOljr3QltDXBVNWbt8qeae/tHgQvMxFmhW3j/gSqHXLcUZhD0iTKlkcitO2x4ZEkRMbTEb59MJoyRJQzAzYVb+xYl68prWm4h8ajwObucGxKmP1316bMaS7pT07blBQ41Bt4OTMKLuTsNlgtF7HjlPJf7sEnsv5fLBCJwyfDqV4AEAjCdhXOGzSckJUFtQo+C0/5sGXM8GYwuHObP6dnAeGNYlGipcukKeG5UXvY7SEpZ6FPd2LXJXoi5HxaZrU8xPipt2kjJBjPdrkVSztnf6I95XmmU5ZCOYC10xZKBo0nW3j88ufSkBhI6dRBeE42Tvq4GwTtj37sLaJhRybc/C3qUriJBzcJ/3fBKYJA2SYDG9K6ZoODzfMhPTePOhBCw/vr3s/QGzUuazc7AWKtvbXr/AQB6UqboZRKjDhjK5QebslRZ4sLhrJMuzJjJs857D5wlkjGZPRpBrOqGgNrmbZYIlP/k6sAbrr4mswmgCMGBvBBQgyEUcqfMn2TPI0I6JSzNFyWBxSpOtxfd7b+RD+y94mU56HSJ9QOQmmc+bYCVqtd0HDj8x+DZGjqZaO3UhUFoKBJbWRynZ6RqMG5/zeULis5cIuzgBLKucMGpcGT1uRBWROHvVvfynZywGGNEu8FHkPZhq166sqxZVgYdBA3YhWohvTqYRYfYtPi6hPyzoFGBPKCpr7PEg2K649OY/rHjkRJjRnw0oSTfYOrpSFFbpdc3qj+OhcAC7hSqWnq6BbZblDdDMQGE28oSC+IkAwkpRq8tLy14vhPwsyxNCwUYQvH+Kn1w8UZqgltgmNcGJ6+CFqbK+EF+iToiPBf8cmPvji3lpMa9RTJbukdIMkqxLAyZDt9yJDxtTPzawcpq3M4Ba5PswMJT0zH+M0m1xrjvoh1O0Mm5xJhHF540rRx45q2U7SVzcyLT+MswdzzniqlQlKvAQLk0cNccTAS/z7MR3mTbWcpXVXQKxeVw6I/2Fug/AS6BjvP8nuKV+l4RRcGqQPNgBa0p9UNcYKJi51k8Ygq7wQqOX4VBUN7qMRNWWbeuiLtzfqAm52JCYztXezCb5Cd9d926IDUoLQIiFExuPKEsconoibQSV0iLavoVuqSdPxbD4o6lRyDIWuZwq4yzvUiNOvuAh3TmH8L8sw9qJGAvEnyG3tQ6zUccfPV6zBYaqzOaI9/03seWq21YnWETOC2chIdUBuwp5Ndx7VMBshs/cB1u1vd2PrBKMUuF3wz4SvpvDUVtJvFqfjbyoVCtH2WN1vMsPDXnnFEut7oy85lDG1yBA+VHK3gzjNlre79vYBS/yuSqZrwk5I+Hh/VYBf4pOA1EHS6bG4BAZ6MG0NnpD4BVXzHAoPrOoqm0mVv32saFpMRARtK5rE9zDL2RZIql7oAQZXWtiyxPXob5zw+Aa6IG5Q2d7DRHBcD4XavSk0sbU+qDYSEg87WCskc+2vIjLeFWQ4VKC/AlaAS8q9NIifrkh4o84QBwJUJ8quxJEWZoJ6zspOjhg4fuzQvALDJpoI4I/rePR7A+vmJM964eGRf/Z9GNTIw9sf6kTHdTdGlsoI8fIn2VKzKld65he5YTwS+TutQp+YhNiyEsLZqmEG4z2QxDu7UFnBdYchGW2rH5PQfNWSLEObc/FnfkNoS48/AnVkHgy+Kmq2XKShK9DkVJTLLqRjoSUcORTEuzRk3ODQfFVxJSVXvMTBo99nRl7Hn757V+/Dejibt3ATaqmE3ubdaMvhdlZrDNzETWGBUs02oG/yZ3h/JJICPRpm1KXNRyBuZXxAK0rtwAQh+56YhbBA76kIGF5BCGXGSfr4mBLJmdGx/GuKrkCU0F3D5dRN+358/weSM/wDY4frgF0zn6Aho186jKbmkO9SqY385fqIk0JRQHQ93WdAvdz4inlzIn2gyrb7ot4IhDTrkByH4IuvAU/mii26/DZbMuYqk08SknYDTuwEUymjAl7TikquZ0hHZI4i6G7Hp+ZP7N+OqWCtP5IovfVxoERpclLAkpJdKMHHDmHwfFSzPyflSDZeSSib7OGGWGF1cKotZp+C1Y8jNuY73z8S3FOMflmz73JPdHpgMc74NiOWpjuIaRtB3wMVgzpnL/vLc3E2zPtLGRUNcaz2ySpRH5bhMqUxSspBjMDBEh+VqtNb74BG4KTkU2QipOyXghLpE7/IzQ4S3ZtgGsOtYLHt09bKi8gFfQIKSU9tWm0YeOcOaJWhCVAZMNWE7o5Acka8S1dPvkngOEE3aiMYPMEr2a14PayjlvWOhDbWLs3wb+PmEPxxJCN+dDybmO35/jHl40oe6G659vXzV92GqJlphOBsEOmKX6xVqigr/6dfTzHIEoBqR1F8AasxWT9pJzD1DHd93ioPV9ZM6gHeIfEiYxZlk7MFmFwzTUHQj31SpPTYt77EmOvspiS0hFTz76itAw6I0UbdsKRy0duf99nIuf1BASWZKd01eMS8VO8Gv30i1/aLsrfjj6QmLbwF982iKRfp3JUHmm/Kehqhd/fiEkBgdUv0oRnc/TKO/VdtQ77sGinAfYbVZbFfhEvz47isVbu01NVIWZhjbTBEEBFxKqtIWvpzY1tlnhjOYDlIJvKUWeecU1tfh68k0cMqHnwrbKDzGNMWW0pbZw5nq/2/mj5Zsc2KLm0a0oJpXmf4hweqByEgCeXEbv2EPdGJofHkM3gWrVGL+FuJ9Oj5jsNsyMgGltj/ME39hj8rZpxHQY7tUVGNLYO+BJygTdANJMDUNXxh1SXAF3IZDU194fLTwddvmNZaPyO3+qk6N0mGiI/N7fE1s03Q9UD8PplhQXDk/S+GX2yv7VCgMmrKvfV2NVAMldOKQHwVl3ixhK5IB6m34zm1ZkuMshH0syl4wUcbFCUy7JmlaV2PBKrDHchX1pHojw+n+taSU4IJcGUyVgyxEh8OYOtevcMl8tGrukLPlW1lptcc8S0QAsKcGtKbMIyEr3LUk9nFn3j4wM1HoWndZC5xwII8hgnmJOemZvT4pRxnItPQpS/OOp0N7gJxdwAzGufjSJMyR9gqJTBln9wySJ1D0xSY+lDi1Hv2JHju9E+wRzaSLE8Xhl80s/sTUUvqtVqwNXsBJmCj8CdyAgubtmpBtxqsb9y5KGltvweMM6VEzKeTUZGHcsfNdYxfLvIlTAQ05lUE2Y9rTTu8tsJKJ95Ok5Bjr6mtfBAeNCyMVNaDguCgZ2j+PFfnPrZxftm1FKsl9eAzQ4kru0z0Ss0N0txZ9Kmlpw3J1324RNWwIbM387582jU1OLhOoKRxIb3b5uOQnjev2PLuGpNuvUi2OX5UdqRb248Wq2Ssc2jtyWXj9wU2XT0FVIAJdqW3/X2U3SZF5ORHKXsW4XLXOMhMWMtTx+L/zpjBGiR6T3v0mOMrcDVf1faYNINxKETCwxFA1gxpxx+6er4xPbiq8zJgY2ZA4R6sxy5+J91HQHPqpcmvpjpyC1fgjOnnzM3reRmZxE5Bh3dWwsI20r1QxT0BFhjOQbgn+pWKR5UbZmWey9Bz8SesgOikBTSlp1wYQUZ5Cx1s+5cM6mDVC7g1C/dk6Q+PlIwPoNRqj6QUx99ZapZiWZRc6TUtRJEVnPj1M8PHsNKwOzT0bvE7oYJo7c8fCN7Fmd2CABPZRzOiJ3WYaFMfgXvQO8+P7vOuhb6Lo2pmDoL71PrjbFGkMjEJB1qUzjRNwAgSg89VaJR7bUtU3Ntp6AVBXcqVirobx8X9sqRtr0BQRq59Due0U1bkKRgTKzx99KTaTcZW19Pt+PeogKAJvrXn7L8QC6nsUIutvQDKetv2+P7NNbATBwo5XbfhK7W07SLrjtImJIwuWpU3E70qHjCVg/PYKMUIDb7TWoQy8I+fffPvfjloIiBbEVXwpRDTHE0lbsbZFCi4YflXDA+ghd+djeHDRJ4+3aFDjdYkRjZk22vYE+jSpVuvKUNuVwXhxiR3oHyA3QUdifqyw9VzJabihkW7NgqnjnZB6IxT8OOgu9pbjr5cTLmc9uZnsSQLyuAC6te+gULro/+9h38YT25qCc9T4+V/N/3ojEMEB0cNv0OGOYfodcsytz8UeiwdAYktrmcbl58+5vFqW6CwZunn2Q3izhAD4cQWoimpaTtU5NqgoZ82vSRt7xlSZGW/f3oo1IknS8StuAtUXOAmySy+tJwKLMk8jOm8zOz2CbaNMDiWWlbUXg0FV+b3uQenhty+ej7D+V/YPijjzMBhFf6h8+zoL32CZolsXZQqlri1QrwFBAzt3JbFeMBWrQBPkq+zIZ23tSuit+aCAdjRZoDRh2tjG+qskmo3uRfFVA9j++cQI5Gvkpo2nFc/6NOW0KT//KX9nX1JLlkpwJzXZxxjV98oyLJAehsigF5XJCTlZociWC98lD8NlACGCH4vVj08NoW1y/Y92g3GpPl3sXv6KkwiTn+xXfsfSQWpFJkM7zup/qpXmqyGJyzaKjY01TSIcekOuIemBa44VDFwf5R30DCw8kV2zgU2oA8PgDVOfdpN7ZWb7XF44iv44EPdLMYiukY1QR8b6FrsOiZugV1MdD+FBxRHlZVATWHpAdAJCg+77PV9YO7rnhIXmHeEX/1BAEC3hyrKlvqusV/jvA57ISmLeci6p4HeveyRxaWp1LagnBVtobgrsRPtz8rM2voFnORc/z74twUjjVkjgS1U+u2BFgxZuXrdHcKeitfRgVJeAmVM8P79gizvCdd06+pZZX6+vw0VXBd08irWThzMzOCvBkdlVdM9umdEepUa0dIjtnCVR/a1Fw5yZOAxldZL5mpFaBDHRbgxyyCjBQist/rI95E5jK7XMFKBrHk51zvlBI9C1ovRkO4Uz+MwVk74xGG4mQus9D/WiEeq7BS9ZuB8XdlKuWWxCjDFvXYM5+SJy0ZVXyOBKIReinEDLNDzBkkchuYKgD5A8Ok6B6vGNdFcP7zjIPyr0gXDqqfWB9c1ERiKnNhghwfMA9uBl4by1QGbzp8orGQcbg5wxicKve1oWOMJacou1W0noyGfciHoyE1xgsdkpX5A+/BQRUBcblhY2/eaitzaeOR2j0dtuSKi9Pndqiy+gx/QvuHDbprrQJJsrMCyNGXxnLrAF8MAXVIVTJjiZqzdL6wjJCh4bGO3FShtcqp3QLuK89JdO4LxqjyeJYJhnhSzfTRTXZwIFFEdf9mFoUWdGsBra5CehEtxWMfT9O607lBRFGekE07ByurebqFp4z9J7EiyxUSkxLVXiavUD1DP7/QJn5Prl1JtNwY2NGQ0zAsolx9t/zRCewPnY1ppVIwC3eVSu5wznSu65MPavqmk3u2DCyyU8A8AnEvz4Mgpd6MGem74KI5XJkT0fCX3yyOZ+HqtFuAf2pe6d4NdaALlxDjlA3gDb4ydZTgJM+oyeskUY8qPMYDyrH7WvprE1HxSMuN87fnae9tjKITosX0msyRgeMHpXHbLhTEuSjDmReJ+qXZe5XVRRhTZiUbYi3Rhodd/LzTJ1OrVuUL64yjzHAcJjwI48xXSP6/zDbzjS+OGhQO22VxtmZ4EqaJH1uYK0Lle2ZB5hl4H6qlCZA2hnxsh7CXAlTSEwkH5x9wxryN75NiIVE3qyHeZSPBCjobSj7qEKQq3q+GcUtae/4ia2wa9ZyrHwoAzymh4f3387JhasUisLuRXhNLfKjHlSPkCm0Urc2usu5/4rDsPnPImbIE00arsd9qR0Qw+hZhBYsewGtGdHD5LMP/K1a5C7CB46lbwEYKucSkhGt10jsbgrTpEMyeSm3whbWEX/VQw4U+bKgpKsNdCZZfkdMjWrF85p8+lCYeBQj6tEh2ywdLBBIIfZdiJDwzLHkC8Mvxjv3IA+X6lJc2TuqimvnbEaF8oV8osxlbjhQ/tHDU2M/GVAlTL58ZCdhysKvjahLSgrrK/J0yW2ba4BleTh4jX+fXrVzgOe8PWc0Aih31xW6tfObs+E8aNoE7OvzDzqt29xR5q7fDx72XiyCh42iQu9NqtUPxvvoGKZEhtHE7NqanURe+4Iglkq3voXG8FBDOpw2B18Rcswy+AgAWFe9uw5sG/UPQ9lrrkKrSI9N/tfgx36f7rFa414NBNLQB6PNrd3xADn6yfG9xE6ziwc0j8Uh+ICbHcEKPAh7JihvtjZZMuzuoDA8Us2L2r7/HtiEu4Pg+QJaoJ7y2V+QFZ/9wsHZ9YohkXH2/a1QOgKYQ/L8Ug6/PHrfsbC3yksJzOIjth53e6Vbvc0w86/0Xb7UNLv8OOIpKwv9v8QvOk8oooGYe52gPZqhxKCOC3pALfcRVY99zHxwDKkQWa6MestoLeRgsAHLz26wtBWYZPxlxLwgChnfNJEINB9Ec/VUjLh/SNGTKKkHxDsuN2/aMR+ogu2eI0VLwe6EtdfN/oPmJmUC/Khfv/9NiLwHHVF+22rlrYXMeQ9yTUyfa/MEZQyGF0EPNB+jgdM8R3pzjgchP13BmU5cuNFBWqOxN1x5GmGh2Kgjl3l+XnvEbF7C1xmzhUaR5Q4kmjSXgpPDYT53+jSfkTR3oJO57bPATFoyVRovE0/tVt2ixVpo+vBM5BM+q4fT9/LLrn0lbnECSFl0tlZYg9z6O8Mfia4lyEi1FDir6qtK8yCvycsi5jl7c7Hbw+sQxX/6JoTulnkD2JWki6mtvIBxLMW26iPTuQYhuVz3U4v7HjeYccKAEbIJCavzRdFXnzP3eb6vXn/gzxFfEaNRFjBZEtgngasvwMWmulJEd/E4R7O0l5BretpGHDJAw9hkPI/YpQ+q4ENS+4csEDkYgs2gBBAmH2XrVUj2glEYrRoX85J8+M/GN1bhTGNdkok+pPhSU5vexD9YSsK9SS9H5dX88FJImY1jmQ0nTEVQY446vQUl33J2x85znHJyqiXEHDkn+oMZrEpmrd4qcUvakDEnBFa4gcjCgqcU1SuUDOfXwA54wcrCTlT3YKd5Ntx/XKmDfZnQLpqJOLnVBdHwgCU7mXy7OkwCtj0x9yzsdk4Lobm6B1Dq2r0FKkN157aArNGM8pJvX760/QGMfXMhczipZWg8sd+4tKD4+QbE7BLIS5ogeoIG8D3ClKftnSHSNFGKmQFsAbYeN5ATHBvTdZXaDjcOhdc8ph8zNs/gaAHG2NPdNXnG/YOlqtWOlIg/xp4DDXTZyOQq57ErPWGC9x2SigCEYkFanC7KFHZq2w6vh2TfeXTnq34i4gNYJ8tKCpsp8uqA4Jpxmg+luVCCtTBwyfPqNU+Rmgj3kE+3QeLE1rxVKD1Euyw6Q55EJDl5PlMoMMme3suWjnvbbktC4M7EthwnywHkIZGe6hZ2Q4nV75hDJ9vrMmziOGo8V5V2ja81L8tkKlcwIaSoKFcpYOaA9PAOl0hfQXdYDBp2aZdpg8ufmlUHS6DNYVhPEtQEpcNWbMaZz9/+P+JocypSTX/j/n79+2ezcyx/JYFrPHp7yRMJKTsNKrrjPX5qPKYKrjTQB6kRIXOWrZcPXZS69WzfVvKBCQ7TCNnmCcq1QCdeCT9frpuyLqah8pT9MRDWgfJqvz6XWs/mmaqMaZALpjUk9dEtBlwIWsPR3gB5KGpODBxjKghbsECJejZasoZa2n5P6NbwB2mQIj3lVfogcEz5FNCpDZq0JLVFUjKJA5xo9tvwUqf4vAaCG0vhfbp3T+9YJZ8ygrUfgj9w+w++1u6XEngAp5D7qv8sPURpBDsLm/6Y9ljzxfXSRDoqxCQSuwRHhnaFqtOHpI/YcsBLvOyqlqLieuhReFjfX3dPKPfMnusvsmiKHHfvoXqhrvG0BQ6xayqmEnuWoHfxYFeOtxdXExxEpcmYjYM35xQs7RG1AbyAV+ug01l+CSEKry/rMP3//MRqsilRU/Hd/JAMKIpHkRTdmALKOuYHCmmRp3u26q9njsWzWYiSdVNpYCDWHnusBzfCFbGWQKAva1kKj0OEzhEcotooQk2l499cfVlh/SLDiKndVR3T4bkPhdfZta0kQPWhDSkXD8+ySl0GkI3WQcBp1vEBdzdVmOq0qhrE1t0QQisusGaTcWsB+aUCCkCie7ZzvSubsS/MB0I9HQk1KY6XtzNi3VGgryiuMcVoKNu1Ka7vi4f7RZ/kLC5JewXjZJk8v7TfiT/izjfE414fAO5bY/qO2ub7trTSDF55OcXQxGTZb4nyZTm6Pzc9+pi8uz6S8JKuxhgajGOD1x9Fo44w6zSwp5oiQGZalBI3Zl1i83JgcpQJLnXNcKIzHNZVepxLYuA1FTc1pwokvBH2Aj8dDaync6JtZOnCYzpp2x8tRBIK+Z7jJvVDBL3z7AOqAM9RHtpCIQWbXkywt/4W7U/F6IgS9yYNb+caU3L6NSQYTWImUg9qb02gfaS8sgDekj4WTkqVx1s6OO4SOuEGf3gwLemJr0FJ2evDe3G7WXQtC+zaPsbbQzYMWNCvRkTGVfjEsr/2bmv7TUjELgKjXgoc4tyb2M5g1QyYftVEGFbWrRfTz3f931NjAIBxhQCBrh+RM7teoz6YO4EaZKFrkPsKPrwgTUxsuUF1RYvtrAZ/GDHxPWmp/fdxtC3wJR0qkrW7DM7UTWMw9WbAuSBr4bx99v9o4N7vHMuYo28rZnw6FMKOZ7wbSlnxbloTTTjrO7CjpQrJg0a0lNBLk6QyvxfJXJ+IuI4KXiEPrdW3AoPaiXvSThKBbIb/wn9r4E3ae8Tnlh+LMzn8G67AHjKaLaq3lRmii+3rEYBsw/NgDh6Fn1cX0sa9BU0BJdFwNQPi37jjzTdRz7kZsy9Hic12NFnLtuSWXCfzGWKsSCZvOpGwqfRLIP80a2MpNXjVntwyp3Z7b9QU3CxEBXd5Lf2ajBTBIC/qzx37sOC657IdKjmkbsFDPTLNgyw72Q3HHOxvscZXi2ai8T4a2TLtw9KNEu0acuBSOSI7qqXVT68RCY+pHCDR6i1ntSG6bodynQpBo9RwM6hijax0YwkXkU9AihF7nE5wzhuHn9CxxeXW2RtQ2/Q7U+WAtEGaps1rj88I+/V8MBOPuYctTlvtQPmpbTKwhCpSsr/3sdzjkSKnR8/Nw68CxzXOG3Y9uQxs3DlAdTBly4JrAmgjAxcvSkfMUaaNjizHyuaCUoSaysrdjSLE7VUmsq3WD1RAtT59nH2qseJHaYHUQco6W+fSVbhVv7XW28g8hGGcIT1Shufxgt8x5qvYIhC1eaarus+bPhR5iAfxQoGyX5kxQKiKK5H0fsQ/5I4zqXWfP4tZubMprYxQMm6evqxGtbKBz0s2D0+unX7ZEvBwvKyTxJ309EWGnFXCmpoQqDBMJEkGodPeRSdvz8Uvfxe8H47RC12BkZCRM+b/bSnLvHWxjWoS5pUC307awfMDv5E/3BlotdB/XYdlx5axECETmLbtpNUyAlUEdOGZ/+LU0E+gxCsHMucNp9F3PiFlC3eqsd4W8ZawD2pVWYAohI0mu7JzJZRKAMZG/vCG5EVSHoYjKppiN0Yd+zdDxCY60czdFtJsw9epsP4e2b/m9/keUrRzpE9aq0IrDJOrrt1UUOyAcOVZGvfuYd8IxjSY4CDxCSg+R1Cyt7cY36Xhve37Z+ejh/MnWsElAJjYXQm02rknfFI1xwv89MW7U3hV/X8KgrDWAyebMG6U3VuB9tBjwuZUg5pzuxwUmtenKp2s+L5kpZWM6ZoLDDpCsDjdCN3M+YY0409h46Z4i5Udt2eJIQwWhA5lhCRLr//xE7Bv7vuDFbzT97RttHSnLWCh+NJe2HUAfIbZcMLBFp0Iyj8Cx3BYs5e0tv4gklKHiewFIvS8IaQ2KdBTtzTS8nVxxKMtn7yDRvrBU0+XKDnroXwkU1cxGKdqIYVjtDgEPoTdsXNJ4z/6QMIRBzV144iOca0SUN6PuTRNV5W9tkOEEnSHbd+4Ks5YUtV+pJVv+VnGiWhMX4j9vVXxIN/IXwPfsqE47Iu0nJxNtYaw2sS7AWeVwWQscyx8ypSsYYZcizlJazaER3Z6K58fgZrJSHMEQFCX/Se+8F4gAUV0uOQgXIz+Ixq9yUCPb3rm/O/0NQvRkqMFDju6psHs6ZflTYYPsnla02RGYoZ3HDv6fgFiG6KKesyXax5YXrlE4mBASozJDlaASiL40H/p17u/LwpOJInKqslwMfoIv4LICUkT//BXJm/syZcAlfsLBQ5OBXlZcP0rh3ox31qQjfqQtn7+D2EBvzHb8KVBwPgm3qh3+f0tZKl+aQV4qy1PgNC1A89Bmr4lt1zXCieXddt6I51NZrX3aU7bpXDQMC3fkVOLh3CeHw+Qdb6YwV9ay28zCq3//Jy33mVqpHppsorV63x1zeN7DCSgSROko7GSrXnnyUf/cD/NXMkifiU2PRkDXibcc85OJGifEO/AgC5sLMUFA6eoA6OSH2i2XvaPJ+fjSSWFO7Qxi5/veO27ghQT7Z7gD/OuVdvGHRQXunPqWVcFOGV9ItulMH4saftVXTmHdndqfJkQsBjOLNgnj20+dx7m7/tOZXt78G/9KRGs/R8t1FEYDfdgAAQIg94RPNEs/HhuTtepqB/y6Q00YFXAG95Pnq0lFGTth6eSEP/E/PKkPR0CsZ/Id+eZ3KI9dzFMyf6lZv+UXECjs5Beq2Alu/b6ZimPM3wunRhgmr1zZlEH4316JYNLXQmvSADAtDffJ6HIF3li3t75pVdLljXAZbZhcr0t86Ag9Jh6geW0pSBmF/TkDpgsKsPHTENP8xdPZWOE8vnXv6KV6pEcLdAWRs3i/XGKVxZgaBXhHQKsvwLQ2wf3e8nE5r49SkMr9yGZKuWwPffOH8Cu9UMjojfWZwhi+Wrzrx2XcrWj/B7JdhB2cOtRLdeiotIwdn1enFikJVYu6Qhxlw78X1ywLQbUUOfqBSkayisnhjRMhPDbR+dm4hMiD3xnl67NNZLwZ/psn3uJFmqU9O/+hS/Sl/+c31y3osZJbGyli/g1E2HKFH1eaT5F9ha9drefK8mM37HOkOHaoQgd+ynordhXYTzHl/ur5UB62THS9krw0eq7bKx51pYIznykBjGX1evwSzxrTU77OnUkK/+n9qAV3LsOIQwMxh/TpNgk42Wf1+ns8AwzKthYq7vMyuKRw4lKdquIZ3/zAk2nNJ0AmvVyJ8JxEtjlI7z7r//cidbvAApdpfAnRLKxXiM97g6iP9KToBNerkT4TiJbHKSV/72SErKkSSI1H86OZ/YZKCQYLEL4CM3DWxTz/hpWiUt8uua1CUcHWht3bLJ+xNdnZgO16jMP8ZswksYcXw7fOEQF5UJ3lrOZhL///hfT2bnwBY5aZix+rD2Qq0LiuVrNtYrc8FWFlElxZOw54NYLcgDwoWMV0S80FmZuuFIZtFADb3+dyYiIGP+osDnBadlc7Vzvk4k6GWPqG0gRy3SqPRqMLZiI/j6VFGk/rrTc6ja/4HONOIlHNNxSERLKHkD4qw8dMQkxsGBYB9qEUo39za80Zo0AqBozjkp7fqcYgCogcpZV1UxmV/Nwr2QbsPRIao3kcymTzqxkGKiyTdFFqKvOPlevtGqY31SN8DHhsByx9K1GCqj3DPsYBKLwWdI70pcv/lpenukMl9DO+cdVYosFwzOS599wDwGwHs3PJ4g/wnDHTLokDB587D/3A/zVzJIGinEHjUEQ1+H5wVHGZWMGC/vNJrZOIuidG1pa78lJNllLFRJkeXc2gyOtGf8UZMnaDlQvEyg+dCgGdpsQIxFTqnPhxvWPpSRLTkMzA6YdDd/T/bP38HsIDfmO34Up9P/eyZ1K4yQP0Uj6SBH5s0diul+M9tTF9SiNYBG0uDewKRG70jYMJFucn6gJ2MfuTk8upqAwZr/4y6hLiJ4I6fpB8EDrKQynTlHKoNF+GeYj1+YBYY3sNC/C8UW0vgTollYrxGe9wdRNX/vZSOW7S//0g+CB1lIZTpyjclfty//ocztIBk1ISh/+MCNyVuNuMc/+HYxd/R4Sld5g3kSm1QJALxntAAKW250G0hrnlFAw+Z9D1rU89vk5LsJEFsaO8M9l8+O/EUWR9mYt4u+BkyPEn92RsRkrQ2JEnKKwXBQzjUM1aILwtjjZJANWvk6nmNdF8If/pB8Yw2aegJ/6HM7SLzeuOOjOqWVwBXseos6x0zzrf/VJSKOr03CMF0eRGm7mOCeoR67fxykjEkQG6RRWhytN0xFled4+N/WB9/Ob7lVbobAlG2Dp/tn7+D2EBvzHb8KU+g9lr3R9n3krN+jrMo/ZeNPzHZa+EmjeHDtdF5nqFbjnnJlcSjR+JAzWMaKq6vPmJPnk9I1KkLOcPm3htg9VyqMn8WosdOuGsSUXN9Vd+EMCkkbJyxO+ry6kHQ0oZkkvaWVHZxuxstrAYzizYJ49tJSG4cFmE/B9gNzanRR77D6hfCDiqwrHLqyhdJIt+CtHik5ppXGl3V7QPenEQJcVzo1MWXsL3L8vK2JqsUHzcWrTNSQExsV8VU9ws0VnuTbPIEmevQZrRKFobxNyM8u6QYLd8FiuNLur2ge9J8k4CJ8WVOeUyGWoLzp7Axcax1LgxQaEXO2XYuQWdpJ3J3V1DQe8RnZ7g4REKgnW3B3oOtstiIWahqG8KUrvJ/4mVJKb/APNnC3lNAAABE6/OGN90Ez+rOajOyTD52F5L6kZfB0VlPOdht0AAAAAAAAAAAAAAAAAA=", ct = "data:image/webp;base64,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", lt = "data:image/webp;base64,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", ut = "data:image/webp;base64,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";
// src/generator-visual.ts
function dt(e) {
	return e.is_connected ? e.e_stop_engaged ? "estop" : e.hasCriticalFault ? "fault" : e.is_exercising ? "exercising" : e.is_running ? "running" : "standby" : "offline";
}
var ft = {
	rca: {
		src: st,
		width: 1e3,
		height: 626,
		description: "KOHLER RCA"
	},
	resv: {
		src: ct,
		width: 1e3,
		height: 667,
		description: "KOHLER 12RESV"
	},
	rcla: {
		src: lt,
		width: 1e3,
		height: 667,
		description: "KOHLER 30RCLA"
	},
	rclc: {
		src: ut,
		width: 1e3,
		height: 667,
		description: "KOHLER 48RCLC"
	}
};
function pt(e) {
	return typeof e == "string" ? e.toUpperCase().replace(/[^A-Z0-9]/g, "").replace(/^MODEL/, "") : "";
}
function mt(e) {
	let t = [
		e.device.modelDisplayName,
		e.device.model,
		...(e.details.generators ?? []).flatMap((e) => [e.modelDisplayName, e.model])
	].map(pt).filter(Boolean), n, r = "", i = !1;
	for (let e of t) {
		let t = e.match(/^(14|20|26)RCAL?(?:A|0)?(?:QS\d.*)?$/);
		if (t ? (n = "rca", r = `KOHLER ${t[1]}RCA`) : /^12RESVL?(?:QS\d.*)?$/.test(e) ? (n = "resv", r = "KOHLER 12RESV") : /^30RCLA(?:QS\d.*)?$/.test(e) ? (n = "rcla", r = "KOHLER 30RCLA") : /^48RCLC(?:QS\d.*)?$/.test(e) && (n = "rclc", r = "KOHLER 48RCLC"), n) break;
	}
	return n ||= (i = !0, t.some((e) => /^(?:4[058]|60|130)RCL/.test(e)) ? "rclc" : t.some((e) => /^\d+RCL/.test(e)) ? "rcla" : t.some((e) => /^(?:8|10|12)RESV|^6VSG/.test(e)) ? "resv" : pt(e.details.coolingType) === "LIQUID" ? "rcla" : "rca"), {
		...ft[n],
		family: n,
		caption: r,
		representative: i
	};
}
// src/format.ts
var ht = {
	ats: "ATS",
	ecm: "ECM",
	ecu: "ECU",
	pim: "PIM",
	rpm: "RPM",
	gfci: "GFCI",
	ism: "ISM",
	ac: "AC",
	dc: "DC",
	kw: "kW",
	lp: "LP",
	ok: "OK",
	co: "CO",
	ip: "IP",
	id: "ID",
	l1: "L1",
	l2: "L2",
	l3: "L3",
	usb: "USB",
	mil: "MIL",
	rsa: "RSA"
};
function R(e) {
	if (e == null) return "";
	let t = String(e);
	return t === "" ? "" : t.includes(" ") ? t.charAt(0).toUpperCase() + t.slice(1) : (t.match(/[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|\d+[A-Za-z]?/g) ?? [t]).map((e, t) => {
		let n = e.toLowerCase();
		return ht[n] ? ht[n] : t === 0 ? e.charAt(0).toUpperCase() + e.slice(1).toLowerCase() : n;
	}).join(" ");
}
function z(e) {
	return String(e).replace(/(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])/g, "_").toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
}
function B(e) {
	if (e == null || e === "" || typeof e == "boolean") return null;
	let t = Number(e);
	return Number.isFinite(t) ? t : null;
}
function gt(e) {
	return e ? [
		e.address1,
		e.address2,
		e.city,
		e.postalCode,
		e.country
	].filter(Boolean).join(", ") : "";
}
var V = {
	grouping: !0,
	metric: !1
};
function _t(e) {
	if (e) try {
		return Intl.DateTimeFormat.supportedLocalesOf(e)[0];
	} catch {
		return;
	}
}
function vt(e) {
	if (e) try {
		return new Intl.DateTimeFormat("en", { timeZone: e }), e;
	} catch {
		return;
	}
}
var yt = {
	comma_decimal: "en-US",
	decimal_comma: "de",
	space_comma: "fr",
	quote_decimal: "de-CH"
};
function bt(e) {
	let t = e?.locale, n = _t(t?.language ?? e?.language), r = t?.number_format, i = vt(e?.config?.time_zone);
	return {
		language: n,
		numberLocale: r === "system" ? void 0 : yt[r ?? ""] ?? n,
		grouping: r !== "none",
		hour12: t?.time_format === "12" || t?.time_format !== "24" && void 0,
		timeZone: t?.time_zone === "server" ? i : void 0,
		serverTimeZone: i,
		metric: e?.config?.unit_system?.temperature === "°C"
	};
}
function H(e, t = V, n = 0) {
	let r = B(e);
	return r === null ? null : new Intl.NumberFormat(t.numberLocale, {
		minimumFractionDigits: n,
		maximumFractionDigits: n,
		useGrouping: t.grouping
	}).format(r);
}
function xt(e, t = V) {
	let n = B(e);
	return n === null ? null : t.metric ? {
		text: H((n - 32) * 5 / 9, t),
		unit: "°C"
	} : {
		text: H(n, t),
		unit: "°F"
	};
}
function St(e, t = V) {
	let n = B(e);
	return n === null ? null : t.metric ? {
		text: H(n * 6.894757, t),
		unit: "kPa"
	} : {
		text: H(n, t),
		unit: "psi"
	};
}
function Ct(e, t = V) {
	let n = B(e);
	return n === null ? null : Math.abs(n) >= 1e3 ? {
		text: H(n / 1e3, t, 1),
		unit: "kW"
	} : {
		text: H(n, t),
		unit: "W"
	};
}
function U(e, t, n, r) {
	return new Intl.NumberFormat(n.language, {
		style: "unit",
		unit: t,
		unitDisplay: r,
		maximumFractionDigits: 0
	}).format(e);
}
function wt(e, t = V) {
	let n = B(e);
	if (n === null) return "—";
	if (n < 60) return U(n, "minute", t, "short");
	let r = Math.floor(n / 60), i = Math.round(n % 60);
	return i ? `${U(r, "hour", t, "short")} ${U(i, "minute", t, "short")}` : U(r, "hour", t, "short");
}
function Tt(e, t = V) {
	let n = B(e);
	return n === null ? "—" : U(n, "day", t, "long");
}
var Et = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?/;
function Dt(e, t) {
	let n = new Intl.DateTimeFormat("en-US", {
		timeZone: t,
		hourCycle: "h23",
		year: "numeric",
		month: "2-digit",
		day: "2-digit",
		hour: "2-digit",
		minute: "2-digit",
		second: "2-digit"
	}).formatToParts(e), r = (e) => Number(n.find((t) => t.type === e)?.value);
	return Date.UTC(r("year"), r("month") - 1, r("day"), r("hour"), r("minute"), r("second")) - Math.floor(e / 1e3) * 1e3;
}
function Ot(e, t) {
	return e - Dt(e - Dt(e, t), t);
}
function kt(e, t) {
	if (typeof e != "string" || e === "" || e.startsWith("0001-01-01")) return null;
	let n = e.trim().replace(/(\.\d{3})\d+/, "$1");
	/[zZ]$/.test(n) && (n = n.slice(0, -1) + "Z");
	let r = Et.exec(n);
	if (r && t && !/(Z|[+-]\d{2}:?\d{2})$/.test(n)) {
		let [, e, n, i, a, o, s] = r, c = Date.UTC(Number(e), Number(n) - 1, Number(i), Number(a), Number(o), Number(s ?? 0));
		return new Date(Ot(c, t));
	}
	let i = new Date(n);
	return Number.isNaN(i.getTime()) ? null : i;
}
function W(e, t = V) {
	let n = kt(e, t.serverTimeZone);
	return n ? n.toLocaleString(t.language, {
		dateStyle: "medium",
		timeStyle: "short",
		hour12: t.hour12,
		timeZone: t.timeZone
	}) : "—";
}
function G(e, t = V) {
	let n = kt(e, t.serverTimeZone);
	if (!n) return "—";
	let r = n.getTime() - Date.now(), i = Math.abs(r), a = new Intl.RelativeTimeFormat(t.language, { numeric: "auto" });
	for (let [e, t] of [
		["year", 31536e6],
		["month", 2592e6],
		["day", 864e5],
		["hour", 36e5],
		["minute", 6e4],
		["second", 1e3]
	]) if (i >= t || e === "second") return a.format(Math.round(r / t), e);
	return "—";
}
var K = (e) => String(e).padStart(2, "0");
function At(e, t = V) {
	let n = kt(e, t.serverTimeZone);
	if (!n) return "";
	let r = t.timeZone ? new Date(n.getTime() + Dt(n.getTime(), t.timeZone)) : /* @__PURE__ */ new Date(n.getTime() - n.getTimezoneOffset() * 6e4);
	return `${r.getUTCFullYear()}-${K(r.getUTCMonth() + 1)}-${K(r.getUTCDate())}T${K(r.getUTCHours())}:${K(r.getUTCMinutes())}`;
}
function jt(e, t = V) {
	let n = Et.exec(e);
	if (!n) return null;
	let [, r, i, a, o, s] = n;
	if (t.timeZone) return new Date(Ot(Date.UTC(Number(r), Number(i) - 1, Number(a), Number(o), Number(s)), t.timeZone));
	let c = new Date(Number(r), Number(i) - 1, Number(a), Number(o), Number(s));
	return Number.isNaN(c.getTime()) ? null : c;
}
// src/locales/de.json
var Mt = {
	"common.generator": "Generator",
	"common.open_sidebar": "Seitenleiste öffnen",
	"common.refresh": "Aktualisieren",
	"common.cancel": "Abbrechen",
	"common.yes": "Ja",
	"common.no": "Nein",
	"common.on": "An",
	"common.off": "Aus",
	"common.unknown": "unbekannt",
	"common.show_more": "Mehr anzeigen",
	"connection.failed": "Verbindung zur Rehlko-Integration nicht möglich.",
	"connection.retrying": "Erneuter Verbindungsversuch…",
	"empty.connecting": "Verbindung zur Integration wird hergestellt…",
	"empty.unavailable": "Generatordaten sind nicht verfügbar. Melde dich als Administrator bei Home Assistant an und prüfe den Status der Integration.",
	"empty.not_loaded": "Das Rehlko-Konto ist nicht geladen. Prüfe unter Einstellungen → Geräte & Dienste, ob Verbindungs- oder Anmeldefehler vorliegen.",
	"empty.no_generators": "In deinem Rehlko-Konto wurden noch keine Generatoren gefunden. Sie erscheinen hier, sobald die Integration fertig geladen ist.",
	"empty.no_integration": "Füge unter Einstellungen → Geräte & Dienste die Integration Rehlko Energy Management hinzu, um deinen Generator hier zu sehen.",
	"empty.open_integrations": "Geräte & Dienste öffnen",
	"toast.no_device": "Dieser Generator hat noch kein Gerät in Home Assistant.",
	"toast.failed": "Die Anfrage ist fehlgeschlagen.",
	"toast.refreshed": "Aktualisiert.",
	"toast.exercise_started": "Start des Probelaufs angefordert.",
	"toast.exercise_stopped": "Stopp des Probelaufs angefordert.",
	"toast.schedule_saved": "Zeitplan gespeichert.",
	"toast.schedule_deleted": "Zeitplan gelöscht.",
	"toast.clock_synced": "Steuerungsuhr gestellt.",
	"toast.note_added": "Wartungsnotiz hinzugefügt.",
	"toast.invalid_next_start": "Gib einen gültigen nächsten Startzeitpunkt ein.",
	"toast.note_required": "Gib zuerst eine Notiz ein.",
	"toast.notify_unavailable": "Dieser Benachrichtigungsschalter ist nicht verfügbar.",
	"toast.setting_failed": "Die Einstellung konnte nicht geändert werden.",
	"toast.setting_saved": "Einstellung gespeichert.",
	"toast.name_required": "Gib einen Namen ein.",
	"toast.value_invalid": "Gib einen gültigen Wert ein.",
	"banner.stale": "Live-Daten sind nicht verfügbar. Dies sind die zuletzt gemeldeten Werte; die Fernsteuerung ist deaktiviert.",
	"banner.offline.title": "Offline.",
	"banner.offline.text": "Dieser Generator ist nicht erreichbar; Live-Daten sind möglicherweise veraltet und Fernaktionen nicht verfügbar.",
	"banner.estop.title": "Not-Aus betätigt.",
	"banner.estop.text": "Fernstart und Probelauf sind deaktiviert, bis er am Generator zurückgesetzt wird.",
	"banner.fault.title": "Kritische Störung.",
	"banner.outage.title": "Versorgung über Generator.",
	"banner.outage.text": "Der Netzstrom ist ausgefallen.",
	"status.offline": "Offline",
	"status.estop": "Not-Aus",
	"status.fault": "Störung",
	"status.exercising": "Probelauf",
	"status.running": "Läuft",
	"status.running_outage": "Läuft – Netzausfall",
	"status.ready": "Betriebsbereit",
	"status.standby": "Bereitschaft",
	"image.alt": "Generator {model}",
	"image.representative": "Abbildung ähnlich",
	"flow.utility": "Netz",
	"flow.home": "Haus",
	"flow.out": "Ausfall",
	"stat.engine": "Motor",
	"stat.load": "Last",
	"stat.speed": "Drehzahl",
	"stat.frequency": "Frequenz",
	"stat.battery": "Batterie",
	"stat.oil_pressure": "Öldruck",
	"stat.coolant": "Kühlmittel",
	"stat.fuel": "Kraftstoff",
	"stat.total_runtime": "Gesamtlaufzeit",
	"unit.rpm": "U/min",
	"tab.overview": "Übersicht",
	"tab.controls": "Bedienung",
	"tab.activity": "Aktivität",
	"tab.maintenance": "Wartung",
	"tab.profile": "Profil",
	"tab.diagnostics": "Diagnose",
	"field.mode": "Modus",
	"field.frequency": "Häufigkeit",
	"field.duration": "Dauer",
	"overview.status": "Status",
	"overview.state": "Zustand",
	"overview.mode_switch": "Betriebsartschalter",
	"overview.power_source": "Stromquelle",
	"overview.last_run": "Letzter Lauf",
	"overview.active_alerts": "Aktive Alarme",
	"overview.shutdown_reason": "Abschaltgrund",
	"overview.next_exercise": "Nächster Probelauf",
	"overview.when": "Zeitpunkt",
	"overview.last_exercise": "Letzter Probelauf",
	"overview.no_schedule": "Kein Probelauf geplant. Lege im Tab „Bedienung“ einen Zeitplan fest.",
	"alert.critical": "kritisch",
	"controls.remote_exercise": "Fern-Probelauf",
	"controls.start": "Probelauf jetzt starten",
	"controls.stop": "Probelauf stoppen",
	"controls.start_hint": "Der Start ist nur möglich, wenn der Generator auf Auto steht und betriebsbereit ist (aktuell: {status}).",
	"controls.schedule": "Probelauf-Zeitplan",
	"controls.create_schedule": "Zeitplan erstellen",
	"controls.duration_minutes": "Dauer (Minuten)",
	"controls.next_start": "Nächster Start",
	"controls.save_schedule": "Zeitplan speichern",
	"controls.delete_schedule": "Zeitplan löschen",
	"controls.no_scheduling": "Die Fernplanung von Probeläufen ist für diese Steuerung nicht verfügbar.",
	"controls.controller": "Steuerung",
	"controls.sync_clock": "Steuerungsuhr synchronisieren",
	"controls.controller_clock": "Steuerungsuhr: {time}",
	"controls.add_note": "Wartungsnotiz hinzufügen",
	"controls.note_label": "Wartungsnotiz",
	"controls.note_placeholder": "Was gemacht wurde…",
	"controls.add_note_button": "Notiz hinzufügen",
	"controls.notifications": "Benachrichtigungen (Konto)",
	"confirm.start.title": "Jetzt einen Probelauf starten?",
	"confirm.start.text": "Der Motor des Generators startet und führt den Probelauf durch.",
	"confirm.start.action": "Probelauf starten",
	"confirm.delete.title": "Probelauf-Zeitplan löschen?",
	"confirm.delete.text": "Der Generator führt keinen automatischen Probelauf mehr durch, bis du einen neuen Zeitplan erstellst.",
	"confirm.delete.action": "Zeitplan löschen",
	"activity.log": "Aktivitätsprotokoll",
	"activity.none": "Keine Aktivität aufgezeichnet.",
	"activity.notifications": "Benachrichtigungen",
	"activity.no_notifications": "Keine Benachrichtigungen.",
	"activity.estop": "Not-Aus",
	"activity.fmi": "FMI {value}",
	"maintenance.title": "Wartung",
	"maintenance.last": "Letzte Wartung",
	"maintenance.next": "Nächste Wartung",
	"maintenance.interval": "Intervall",
	"maintenance.runtime_since": "Laufzeit seit Wartung",
	"maintenance.history": "Verlauf",
	"maintenance.none": "Noch keine Wartungsnotizen. Füge im Tab „Bedienung“ eine hinzu.",
	"maintenance.dealer": "Händler",
	"maintenance.homeowner": "Hauseigentümer",
	"profile.model": "Modell",
	"profile.serial": "Seriennummer",
	"profile.controller": "Steuerung",
	"profile.firmware": "Firmware",
	"profile.fuel": "Kraftstoff",
	"profile.cooling": "Kühlung",
	"profile.rated_voltage": "Nennspannung",
	"profile.site": "Standort & Service",
	"profile.address": "Adresse",
	"profile.connection": "Verbindung",
	"profile.service_agreement": "Servicevertrag",
	"profile.term": "Vertragslaufzeit",
	"profile.dealer": "Händler",
	"profile.dealer_phone": "Händlertelefon",
	"profile.load_module": "Lastabwurfmodul",
	"profile.pim": "Programmierbares Schnittstellenmodul",
	"profile.transfer_switch": "Netzumschalter",
	"profile.connected": "verbunden",
	"profile.offline": "offline",
	"profile.no_parameters": "Keine Parameter gemeldet.",
	"profile.position": "Stellung",
	"profile.edit": "{name} bearbeiten",
	"edit.title": "Einstellung bearbeiten",
	"edit.name": "Name",
	"edit.value": "Wert",
	"edit.save": "Speichern",
	"diagnostics.title": "Diagnose",
	"diagnostics.connected": "Verbunden",
	"diagnostics.device_ip": "Von Rehlko gesehene IP-Adresse",
	"diagnostics.mac": "MAC-Adresse",
	"diagnostics.uptime": "Verfügbarkeit",
	"diagnostics.last_connected": "Zuletzt verbunden",
	"diagnostics.parameters_updated": "Parameter aktualisiert",
	"diagnostics.cellular_status": "Mobilfunkstatus",
	"diagnostics.cellular_used": "Verbrauchte Mobilfunkdaten",
	"diagnostics.auto_update": "Automatische Firmware-Updates",
	"diagnostics.details_refreshed": "Details aktualisiert",
	"diagnostics.feeds_refreshed": "Feeds aktualisiert",
	"diagnostics.account": "Konto",
	"diagnostics.account_ok": "OK",
	"diagnostics.account_failed": "Letzte Abfrage fehlgeschlagen",
	"diagnostics.entities": "Entitäten",
	"diagnostics.entities_text": "Zu diesem Generator gehören {count} Entitäten in Home Assistant (Sensoren, Bedienelemente und Diagnose). Die vollständige Liste samt Verlauf findest du auf der Geräteseite.",
	"diagnostics.open_device": "Geräteseite öffnen"
}, Nt = {
	"common.generator": "Generator",
	"common.open_sidebar": "Open sidebar",
	"common.refresh": "Refresh",
	"common.cancel": "Cancel",
	"common.yes": "Yes",
	"common.no": "No",
	"common.on": "On",
	"common.off": "Off",
	"common.unknown": "unknown",
	"common.show_more": "Show more",
	"connection.failed": "Unable to connect to the Rehlko integration.",
	"connection.retrying": "Retrying connection…",
	"empty.connecting": "Connecting to the integration…",
	"empty.unavailable": "Generator data is unavailable. Sign in as a Home Assistant administrator and check the integration's status.",
	"empty.not_loaded": "The Rehlko account is not loaded. Check Settings → Devices & services for connection or sign-in errors.",
	"empty.no_generators": "No generators found on your Rehlko account yet. They appear here once the integration finishes loading.",
	"empty.no_integration": "Add the Rehlko Energy Management integration under Settings → Devices & services to see your generator here.",
	"empty.open_integrations": "Open Devices & services",
	"toast.no_device": "This generator has no Home Assistant device yet.",
	"toast.failed": "The request failed.",
	"toast.refreshed": "Refreshed.",
	"toast.exercise_started": "Exercise start requested.",
	"toast.exercise_stopped": "Exercise stop requested.",
	"toast.schedule_saved": "Schedule saved.",
	"toast.schedule_deleted": "Schedule deleted.",
	"toast.clock_synced": "Controller clock set.",
	"toast.note_added": "Maintenance note added.",
	"toast.invalid_next_start": "Enter a valid next start time.",
	"toast.note_required": "Type a note first.",
	"toast.notify_unavailable": "That notification switch is not available.",
	"toast.setting_failed": "Could not change the setting.",
	"toast.setting_saved": "Setting saved.",
	"toast.name_required": "Enter a name.",
	"toast.value_invalid": "Enter a valid value.",
	"banner.stale": "Live data is unavailable. These are the last reported readings; remote controls are disabled.",
	"banner.offline.title": "Offline.",
	"banner.offline.text": "This generator is not reachable; live data may be stale and remote actions are unavailable.",
	"banner.estop.title": "Emergency stop engaged.",
	"banner.estop.text": "Remote start and exercise are disabled until it is reset at the generator.",
	"banner.fault.title": "Critical fault.",
	"banner.outage.title": "Running on generator power.",
	"banner.outage.text": "Utility power is out.",
	"status.offline": "Offline",
	"status.estop": "Emergency stop",
	"status.fault": "Fault",
	"status.exercising": "Exercising",
	"status.running": "Running",
	"status.running_outage": "Running — outage",
	"status.ready": "Ready to run",
	"status.standby": "Standby",
	"image.alt": "{model} generator",
	"image.representative": "Representative product image",
	"flow.utility": "Utility",
	"flow.home": "Home",
	"flow.out": "Out",
	"stat.engine": "Engine",
	"stat.load": "Load",
	"stat.speed": "Speed",
	"stat.frequency": "Frequency",
	"stat.battery": "Battery",
	"stat.oil_pressure": "Oil pressure",
	"stat.coolant": "Coolant",
	"stat.fuel": "Fuel",
	"stat.total_runtime": "Total runtime",
	"unit.rpm": "rpm",
	"tab.overview": "Overview",
	"tab.controls": "Controls",
	"tab.activity": "Activity",
	"tab.maintenance": "Maintenance",
	"tab.profile": "Profile",
	"tab.diagnostics": "Diagnostics",
	"field.mode": "Mode",
	"field.frequency": "Frequency",
	"field.duration": "Duration",
	"overview.status": "Status",
	"overview.state": "State",
	"overview.mode_switch": "Mode switch",
	"overview.power_source": "Power source",
	"overview.last_run": "Last run",
	"overview.active_alerts": "Active alerts",
	"overview.shutdown_reason": "Shutdown reason",
	"overview.next_exercise": "Next exercise",
	"overview.when": "When",
	"overview.last_exercise": "Last exercise",
	"overview.no_schedule": "No exercise scheduled. Set one on the Controls tab.",
	"alert.critical": "critical",
	"controls.remote_exercise": "Remote exercise",
	"controls.start": "Start exercise now",
	"controls.stop": "Stop exercise",
	"controls.start_hint": "Starting is available only when the generator is in Auto and ready to run (now: {status}).",
	"controls.schedule": "Exercise schedule",
	"controls.create_schedule": "Create a schedule",
	"controls.duration_minutes": "Duration (minutes)",
	"controls.next_start": "Next start",
	"controls.save_schedule": "Save schedule",
	"controls.delete_schedule": "Delete schedule",
	"controls.no_scheduling": "Remote exercise scheduling is not available for this controller.",
	"controls.controller": "Controller",
	"controls.sync_clock": "Sync controller clock",
	"controls.controller_clock": "Controller clock: {time}",
	"controls.add_note": "Add a maintenance note",
	"controls.note_label": "Maintenance note",
	"controls.note_placeholder": "What was done…",
	"controls.add_note_button": "Add note",
	"controls.notifications": "Notifications (account)",
	"confirm.start.title": "Start an exercise now?",
	"confirm.start.text": "The generator's engine will start and run the exercise.",
	"confirm.start.action": "Start exercise",
	"confirm.delete.title": "Delete the exercise schedule?",
	"confirm.delete.text": "The generator will not exercise automatically until you create a new schedule.",
	"confirm.delete.action": "Delete schedule",
	"activity.log": "Activity log",
	"activity.none": "No activity recorded.",
	"activity.notifications": "Notifications",
	"activity.no_notifications": "No notifications.",
	"activity.estop": "E-Stop",
	"activity.fmi": "FMI {value}",
	"maintenance.title": "Maintenance",
	"maintenance.last": "Last maintenance",
	"maintenance.next": "Next maintenance",
	"maintenance.interval": "Interval",
	"maintenance.runtime_since": "Runtime since service",
	"maintenance.history": "History",
	"maintenance.none": "No maintenance notes yet. Add one on the Controls tab.",
	"maintenance.dealer": "Dealer",
	"maintenance.homeowner": "Homeowner",
	"profile.model": "Model",
	"profile.serial": "Serial number",
	"profile.controller": "Controller",
	"profile.firmware": "Firmware",
	"profile.fuel": "Fuel",
	"profile.cooling": "Cooling",
	"profile.rated_voltage": "Rated voltage",
	"profile.site": "Site & service",
	"profile.address": "Address",
	"profile.connection": "Connection",
	"profile.service_agreement": "Service agreement",
	"profile.term": "Term",
	"profile.dealer": "Dealer",
	"profile.dealer_phone": "Dealer phone",
	"profile.load_module": "Load module",
	"profile.pim": "Programmable interface module",
	"profile.transfer_switch": "Transfer switch",
	"profile.connected": "connected",
	"profile.offline": "offline",
	"profile.no_parameters": "No parameters reported.",
	"profile.position": "Position",
	"profile.edit": "Edit {name}",
	"edit.title": "Edit setting",
	"edit.name": "Name",
	"edit.value": "Value",
	"edit.save": "Save",
	"diagnostics.title": "Diagnostics",
	"diagnostics.connected": "Connected",
	"diagnostics.device_ip": "IP address seen by Rehlko",
	"diagnostics.mac": "MAC address",
	"diagnostics.uptime": "Uptime",
	"diagnostics.last_connected": "Last connected",
	"diagnostics.parameters_updated": "Parameters updated",
	"diagnostics.cellular_status": "Cellular status",
	"diagnostics.cellular_used": "Cellular data used",
	"diagnostics.auto_update": "Automatic firmware updates",
	"diagnostics.details_refreshed": "Details refreshed",
	"diagnostics.feeds_refreshed": "Feeds refreshed",
	"diagnostics.account": "Account",
	"diagnostics.account_ok": "OK",
	"diagnostics.account_failed": "Last poll failed",
	"diagnostics.entities": "Entities",
	"diagnostics.entities_text": "{count} Home Assistant entities back this generator (sensors, controls and diagnostics). The device page has the full list and their history.",
	"diagnostics.open_device": "Open device page"
}, Pt = /* #__PURE__ */ Object.assign({
	"./locales/de.json": Mt,
	"./locales/en.json": Nt,
	"./locales/es.json": {
		"common.generator": "Generador",
		"common.open_sidebar": "Abrir barra lateral",
		"common.refresh": "Actualizar",
		"common.cancel": "Cancelar",
		"common.yes": "Sí",
		"common.no": "No",
		"common.on": "Activado",
		"common.off": "Desactivado",
		"common.unknown": "desconocido",
		"common.show_more": "Mostrar más",
		"connection.failed": "No se pudo conectar con la integración de Rehlko.",
		"connection.retrying": "Reintentando la conexión…",
		"empty.connecting": "Conectando con la integración…",
		"empty.unavailable": "Los datos del generador no están disponibles. Inicia sesión como administrador de Home Assistant y revisa el estado de la integración.",
		"empty.not_loaded": "La cuenta de Rehlko no está cargada. Revisa en Ajustes → Dispositivos y servicios si hay errores de conexión o de inicio de sesión.",
		"empty.no_generators": "Todavía no se encontraron generadores en tu cuenta de Rehlko. Aparecerán aquí cuando la integración termine de cargarse.",
		"empty.no_integration": "Añade la integración Rehlko Energy Management en Ajustes → Dispositivos y servicios para ver tu generador aquí.",
		"empty.open_integrations": "Abrir Dispositivos y servicios",
		"toast.no_device": "Este generador todavía no tiene un dispositivo en Home Assistant.",
		"toast.failed": "La solicitud falló.",
		"toast.refreshed": "Actualizado.",
		"toast.exercise_started": "Se solicitó el inicio del ejercicio.",
		"toast.exercise_stopped": "Se solicitó la detención del ejercicio.",
		"toast.schedule_saved": "Programación guardada.",
		"toast.schedule_deleted": "Programación eliminada.",
		"toast.clock_synced": "Reloj del controlador ajustado.",
		"toast.note_added": "Nota de mantenimiento añadida.",
		"toast.invalid_next_start": "Indica una fecha y hora válidas para el próximo inicio.",
		"toast.note_required": "Primero escribe una nota.",
		"toast.notify_unavailable": "Ese interruptor de notificaciones no está disponible.",
		"toast.setting_failed": "No se pudo cambiar el ajuste.",
		"toast.setting_saved": "Ajuste guardado.",
		"toast.name_required": "Escribe un nombre.",
		"toast.value_invalid": "Escribe un valor válido.",
		"banner.stale": "Los datos en tiempo real no están disponibles. Estas son las últimas lecturas recibidas; los controles remotos están desactivados.",
		"banner.offline.title": "Sin conexión.",
		"banner.offline.text": "No se puede acceder a este generador; los datos en tiempo real pueden estar desactualizados y las acciones remotas no están disponibles.",
		"banner.estop.title": "Parada de emergencia activada.",
		"banner.estop.text": "El arranque remoto y el ejercicio remoto están desactivados hasta que se restablezca en el generador.",
		"banner.fault.title": "Falla crítica.",
		"banner.outage.title": "Funcionando con energía del generador.",
		"banner.outage.text": "No hay energía de la red eléctrica.",
		"status.offline": "Sin conexión",
		"status.estop": "Parada de emergencia",
		"status.fault": "Falla",
		"status.exercising": "En ejercicio",
		"status.running": "En marcha",
		"status.running_outage": "En marcha — corte de energía",
		"status.ready": "Listo para funcionar",
		"status.standby": "En espera",
		"image.alt": "Generador {model}",
		"image.representative": "Imagen representativa del producto",
		"flow.utility": "Red eléctrica",
		"flow.home": "Casa",
		"flow.out": "Sin energía",
		"stat.engine": "Motor",
		"stat.load": "Carga",
		"stat.speed": "Velocidad",
		"stat.frequency": "Frecuencia",
		"stat.battery": "Batería",
		"stat.oil_pressure": "Presión de aceite",
		"stat.coolant": "Refrigerante",
		"stat.fuel": "Combustible",
		"stat.total_runtime": "Tiempo total en marcha",
		"unit.rpm": "rpm",
		"tab.overview": "Resumen",
		"tab.controls": "Controles",
		"tab.activity": "Actividad",
		"tab.maintenance": "Mantenimiento",
		"tab.profile": "Perfil",
		"tab.diagnostics": "Diagnóstico",
		"field.mode": "Modo",
		"field.frequency": "Frecuencia",
		"field.duration": "Duración",
		"overview.status": "Estado general",
		"overview.state": "Estado",
		"overview.mode_switch": "Selector de modo",
		"overview.power_source": "Fuente de energía",
		"overview.last_run": "Última vez en marcha",
		"overview.active_alerts": "Alertas activas",
		"overview.shutdown_reason": "Motivo de la parada",
		"overview.next_exercise": "Próximo ejercicio",
		"overview.when": "Cuándo",
		"overview.last_exercise": "Último ejercicio",
		"overview.no_schedule": "No hay ningún ejercicio programado. Configura uno en la pestaña Controles.",
		"alert.critical": "crítica",
		"controls.remote_exercise": "Ejercicio remoto",
		"controls.start": "Iniciar ejercicio ahora",
		"controls.stop": "Detener ejercicio",
		"controls.start_hint": "Solo se puede iniciar cuando el generador está en Auto y listo para funcionar (ahora: {status}).",
		"controls.schedule": "Programación de ejercicio",
		"controls.create_schedule": "Crear una programación",
		"controls.duration_minutes": "Duración (minutos)",
		"controls.next_start": "Próximo inicio",
		"controls.save_schedule": "Guardar programación",
		"controls.delete_schedule": "Eliminar programación",
		"controls.no_scheduling": "La programación remota de ejercicios no está disponible para este controlador.",
		"controls.controller": "Controlador",
		"controls.sync_clock": "Sincronizar reloj del controlador",
		"controls.controller_clock": "Reloj del controlador: {time}",
		"controls.add_note": "Añadir una nota de mantenimiento",
		"controls.note_label": "Nota de mantenimiento",
		"controls.note_placeholder": "Qué se hizo…",
		"controls.add_note_button": "Añadir nota",
		"controls.notifications": "Notificaciones (cuenta)",
		"confirm.start.title": "¿Iniciar un ejercicio ahora?",
		"confirm.start.text": "El motor del generador arrancará y realizará el ejercicio.",
		"confirm.start.action": "Iniciar ejercicio",
		"confirm.delete.title": "¿Eliminar la programación de ejercicio?",
		"confirm.delete.text": "El generador no realizará ejercicios automáticamente hasta que crees una nueva programación.",
		"confirm.delete.action": "Eliminar programación",
		"activity.log": "Registro de actividad",
		"activity.none": "No hay actividad registrada.",
		"activity.notifications": "Notificaciones",
		"activity.no_notifications": "No hay notificaciones.",
		"activity.estop": "Parada de emergencia",
		"activity.fmi": "FMI {value}",
		"maintenance.title": "Mantenimiento",
		"maintenance.last": "Último mantenimiento",
		"maintenance.next": "Próximo mantenimiento",
		"maintenance.interval": "Intervalo",
		"maintenance.runtime_since": "Tiempo en marcha desde el mantenimiento",
		"maintenance.history": "Historial",
		"maintenance.none": "Todavía no hay notas de mantenimiento. Añade una en la pestaña Controles.",
		"maintenance.dealer": "Distribuidor",
		"maintenance.homeowner": "Propietario",
		"profile.model": "Modelo",
		"profile.serial": "Número de serie",
		"profile.controller": "Controlador",
		"profile.firmware": "Firmware",
		"profile.fuel": "Combustible",
		"profile.cooling": "Refrigeración",
		"profile.rated_voltage": "Voltaje nominal",
		"profile.site": "Instalación y servicio",
		"profile.address": "Dirección",
		"profile.connection": "Conexión",
		"profile.service_agreement": "Contrato de servicio",
		"profile.term": "Plazo",
		"profile.dealer": "Distribuidor",
		"profile.dealer_phone": "Teléfono del distribuidor",
		"profile.load_module": "Módulo de carga",
		"profile.pim": "Módulo de interfaz programable (PIM)",
		"profile.transfer_switch": "Interruptor de transferencia",
		"profile.connected": "conectado",
		"profile.offline": "sin conexión",
		"profile.no_parameters": "No se informaron parámetros.",
		"profile.position": "Posición",
		"profile.edit": "Editar {name}",
		"edit.title": "Editar ajuste",
		"edit.name": "Nombre",
		"edit.value": "Valor",
		"edit.save": "Guardar",
		"diagnostics.title": "Diagnóstico",
		"diagnostics.connected": "Conectado",
		"diagnostics.device_ip": "Dirección IP vista por Rehlko",
		"diagnostics.mac": "Dirección MAC",
		"diagnostics.uptime": "Disponibilidad",
		"diagnostics.last_connected": "Última conexión",
		"diagnostics.parameters_updated": "Parámetros actualizados",
		"diagnostics.cellular_status": "Estado de datos móviles",
		"diagnostics.cellular_used": "Datos móviles usados",
		"diagnostics.auto_update": "Actualizaciones automáticas de firmware",
		"diagnostics.details_refreshed": "Detalles actualizados",
		"diagnostics.feeds_refreshed": "Listas actualizadas",
		"diagnostics.account": "Cuenta",
		"diagnostics.account_ok": "OK",
		"diagnostics.account_failed": "Falló el último sondeo",
		"diagnostics.entities": "Entidades",
		"diagnostics.entities_text": "Este generador tiene {count} entidades de Home Assistant (sensores, controles y diagnóstico). La página del dispositivo muestra la lista completa y su historial.",
		"diagnostics.open_device": "Abrir página del dispositivo"
	},
	"./locales/fr.json": {
		"common.generator": "Génératrice",
		"common.open_sidebar": "Ouvrir la barre latérale",
		"common.refresh": "Actualiser",
		"common.cancel": "Annuler",
		"common.yes": "Oui",
		"common.no": "Non",
		"common.on": "Activé",
		"common.off": "Désactivé",
		"common.unknown": "inconnu",
		"common.show_more": "Afficher plus",
		"connection.failed": "Impossible de se connecter à l'intégration Rehlko.",
		"connection.retrying": "Nouvelle tentative de connexion…",
		"empty.connecting": "Connexion à l'intégration…",
		"empty.unavailable": "Les données de la génératrice sont indisponibles. Connectez-vous en tant qu'administrateur de Home Assistant et vérifiez l'état de l'intégration.",
		"empty.not_loaded": "Le compte Rehlko n'est pas chargé. Consultez Paramètres → Appareils et services pour voir les erreurs de connexion ou d'authentification.",
		"empty.no_generators": "Aucune génératrice n'a encore été trouvée dans votre compte Rehlko. Elles apparaîtront ici une fois le chargement de l'intégration terminé.",
		"empty.no_integration": "Ajoutez l'intégration Rehlko Energy Management dans Paramètres → Appareils et services pour voir votre génératrice ici.",
		"empty.open_integrations": "Ouvrir Appareils et services",
		"toast.no_device": "Cette génératrice n'a pas encore d'appareil Home Assistant.",
		"toast.failed": "La requête a échoué.",
		"toast.refreshed": "Actualisé.",
		"toast.exercise_started": "Démarrage de l'exercice demandé.",
		"toast.exercise_stopped": "Arrêt de l'exercice demandé.",
		"toast.schedule_saved": "Planification enregistrée.",
		"toast.schedule_deleted": "Planification supprimée.",
		"toast.clock_synced": "Horloge du contrôleur réglée.",
		"toast.note_added": "Note d'entretien ajoutée.",
		"toast.invalid_next_start": "Entrez une date et une heure valides pour le prochain démarrage.",
		"toast.note_required": "Entrez d'abord une note.",
		"toast.notify_unavailable": "Cet interrupteur de notification n'est pas disponible.",
		"toast.setting_failed": "Impossible de modifier le paramètre.",
		"toast.setting_saved": "Réglage enregistré.",
		"toast.name_required": "Saisissez un nom.",
		"toast.value_invalid": "Saisissez une valeur valide.",
		"banner.stale": "Les données en direct sont indisponibles. Voici les dernières valeurs transmises. Les commandes à distance sont désactivées.",
		"banner.offline.title": "Hors ligne.",
		"banner.offline.text": "Cette génératrice est injoignable. Les données en direct ne sont peut-être plus à jour et les actions à distance sont indisponibles.",
		"banner.estop.title": "Arrêt d'urgence enclenché.",
		"banner.estop.text": "Le démarrage et l'exercice à distance sont désactivés tant qu'il n'a pas été réarmé sur la génératrice.",
		"banner.fault.title": "Défaut critique.",
		"banner.outage.title": "Maison alimentée par la génératrice.",
		"banner.outage.text": "Le réseau électrique est en panne.",
		"status.offline": "Hors ligne",
		"status.estop": "Arrêt d'urgence",
		"status.fault": "Défaut",
		"status.exercising": "En exercice",
		"status.running": "En marche",
		"status.running_outage": "En marche — panne de courant",
		"status.ready": "Prête à démarrer",
		"status.standby": "En veille",
		"image.alt": "Génératrice {model}",
		"image.representative": "Image représentative du produit",
		"flow.utility": "Réseau",
		"flow.home": "Maison",
		"flow.out": "En panne",
		"stat.engine": "Moteur",
		"stat.load": "Charge",
		"stat.speed": "Régime",
		"stat.frequency": "Fréquence",
		"stat.battery": "Batterie",
		"stat.oil_pressure": "Pression d'huile",
		"stat.coolant": "Liquide de refroidissement",
		"stat.fuel": "Carburant",
		"stat.total_runtime": "Temps de fonctionnement total",
		"unit.rpm": "tr/min",
		"tab.overview": "Aperçu",
		"tab.controls": "Commandes",
		"tab.activity": "Activité",
		"tab.maintenance": "Entretien",
		"tab.profile": "Profil",
		"tab.diagnostics": "Diagnostic",
		"field.mode": "Mode",
		"field.frequency": "Fréquence",
		"field.duration": "Durée",
		"overview.status": "État actuel",
		"overview.state": "État",
		"overview.mode_switch": "Sélecteur de mode",
		"overview.power_source": "Source d'alimentation",
		"overview.last_run": "Dernier fonctionnement",
		"overview.active_alerts": "Alertes actives",
		"overview.shutdown_reason": "Cause de l'arrêt de sécurité",
		"overview.next_exercise": "Prochain exercice",
		"overview.when": "Date et heure",
		"overview.last_exercise": "Dernier exercice",
		"overview.no_schedule": "Aucun exercice planifié. Définissez-en un dans l'onglet Commandes.",
		"alert.critical": "critique",
		"controls.remote_exercise": "Exercice à distance",
		"controls.start": "Démarrer un exercice maintenant",
		"controls.stop": "Arrêter l'exercice",
		"controls.start_hint": "Le démarrage n'est possible que lorsque la génératrice est en mode Auto et prête à démarrer (actuellement\xA0: {status}).",
		"controls.schedule": "Planification des exercices",
		"controls.create_schedule": "Créer une planification",
		"controls.duration_minutes": "Durée (minutes)",
		"controls.next_start": "Prochain démarrage",
		"controls.save_schedule": "Enregistrer la planification",
		"controls.delete_schedule": "Supprimer la planification",
		"controls.no_scheduling": "Ce contrôleur ne prend pas en charge la planification à distance des exercices.",
		"controls.controller": "Contrôleur",
		"controls.sync_clock": "Synchroniser l'horloge du contrôleur",
		"controls.controller_clock": "Horloge du contrôleur\xA0: {time}",
		"controls.add_note": "Ajouter une note d'entretien",
		"controls.note_label": "Note d'entretien",
		"controls.note_placeholder": "Ce qui a été fait…",
		"controls.add_note_button": "Ajouter la note",
		"controls.notifications": "Notifications (compte)",
		"confirm.start.title": "Démarrer un exercice maintenant\xA0?",
		"confirm.start.text": "Le moteur de la génératrice démarrera et effectuera l'exercice.",
		"confirm.start.action": "Démarrer l'exercice",
		"confirm.delete.title": "Supprimer la planification des exercices\xA0?",
		"confirm.delete.text": "La génératrice n'effectuera plus d'exercice automatiquement tant que vous n'aurez pas créé une nouvelle planification.",
		"confirm.delete.action": "Supprimer la planification",
		"activity.log": "Journal d'activité",
		"activity.none": "Aucune activité enregistrée.",
		"activity.notifications": "Notifications",
		"activity.no_notifications": "Aucune notification.",
		"activity.estop": "Arrêt d'urgence",
		"activity.fmi": "FMI {value}",
		"maintenance.title": "Entretien",
		"maintenance.last": "Dernier entretien",
		"maintenance.next": "Prochain entretien",
		"maintenance.interval": "Intervalle",
		"maintenance.runtime_since": "Temps de fonctionnement depuis l'entretien",
		"maintenance.history": "Historique",
		"maintenance.none": "Aucune note d'entretien pour l'instant. Ajoutez-en une dans l'onglet Commandes.",
		"maintenance.dealer": "Concessionnaire",
		"maintenance.homeowner": "Propriétaire",
		"profile.model": "Modèle",
		"profile.serial": "Numéro de série",
		"profile.controller": "Contrôleur",
		"profile.firmware": "Micrologiciel",
		"profile.fuel": "Carburant",
		"profile.cooling": "Refroidissement",
		"profile.rated_voltage": "Tension nominale",
		"profile.site": "Site et service",
		"profile.address": "Adresse",
		"profile.connection": "Connexion",
		"profile.service_agreement": "Contrat de service",
		"profile.term": "Durée",
		"profile.dealer": "Concessionnaire",
		"profile.dealer_phone": "Téléphone du concessionnaire",
		"profile.load_module": "Module de délestage",
		"profile.pim": "Module d'interface programmable (PIM)",
		"profile.transfer_switch": "Commutateur de transfert",
		"profile.connected": "connecté",
		"profile.offline": "hors ligne",
		"profile.no_parameters": "Aucun paramètre transmis.",
		"profile.position": "Position",
		"profile.edit": "Modifier {name}",
		"edit.title": "Modifier le réglage",
		"edit.name": "Nom",
		"edit.value": "Valeur",
		"edit.save": "Enregistrer",
		"diagnostics.title": "Diagnostic",
		"diagnostics.connected": "Connectée",
		"diagnostics.device_ip": "Adresse IP vue par Rehlko",
		"diagnostics.mac": "Adresse MAC",
		"diagnostics.uptime": "Disponibilité de la connexion",
		"diagnostics.last_connected": "Dernière connexion",
		"diagnostics.parameters_updated": "Mise à jour des paramètres",
		"diagnostics.cellular_status": "État du service cellulaire",
		"diagnostics.cellular_used": "Données cellulaires utilisées",
		"diagnostics.auto_update": "Mises à jour automatiques du micrologiciel",
		"diagnostics.details_refreshed": "Actualisation des détails",
		"diagnostics.feeds_refreshed": "Actualisation des flux",
		"diagnostics.account": "Compte",
		"diagnostics.account_ok": "OK",
		"diagnostics.account_failed": "Échec de la dernière interrogation",
		"diagnostics.entities": "Entités",
		"diagnostics.entities_text": "{count} entités Home Assistant sont associées à cette génératrice (capteurs, commandes et diagnostics). La page de l'appareil en présente la liste complète et l'historique.",
		"diagnostics.open_device": "Ouvrir la page de l'appareil"
	},
	"./locales/it.json": {
		"common.generator": "Generatore",
		"common.open_sidebar": "Apri barra laterale",
		"common.refresh": "Aggiorna",
		"common.cancel": "Annulla",
		"common.yes": "Sì",
		"common.no": "No",
		"common.on": "Attivo",
		"common.off": "Non attivo",
		"common.unknown": "sconosciuto",
		"common.show_more": "Mostra altro",
		"connection.failed": "Impossibile connettersi all'integrazione Rehlko.",
		"connection.retrying": "Nuovo tentativo di connessione…",
		"empty.connecting": "Connessione all'integrazione in corso…",
		"empty.unavailable": "I dati del generatore non sono disponibili. Accedi come amministratore di Home Assistant e controlla lo stato dell'integrazione.",
		"empty.not_loaded": "L'account Rehlko non è caricato. Controlla in Impostazioni → Dispositivi e servizi se ci sono errori di connessione o di accesso.",
		"empty.no_generators": "Per ora non è stato trovato alcun generatore nel tuo account Rehlko. I generatori compariranno qui al termine del caricamento dell'integrazione.",
		"empty.no_integration": "Aggiungi l'integrazione Rehlko Energy Management in Impostazioni → Dispositivi e servizi per vedere qui il tuo generatore.",
		"empty.open_integrations": "Apri Dispositivi e servizi",
		"toast.no_device": "Questo generatore non ha ancora un dispositivo in Home Assistant.",
		"toast.failed": "La richiesta non è riuscita.",
		"toast.refreshed": "Dati aggiornati.",
		"toast.exercise_started": "Avvio della prova periodica richiesto.",
		"toast.exercise_stopped": "Interruzione della prova periodica richiesta.",
		"toast.schedule_saved": "Pianificazione salvata.",
		"toast.schedule_deleted": "Pianificazione eliminata.",
		"toast.clock_synced": "Orologio della centralina impostato.",
		"toast.note_added": "Nota di manutenzione aggiunta.",
		"toast.invalid_next_start": "Inserisci una data e un'ora valide per il prossimo avvio.",
		"toast.note_required": "Scrivi prima una nota.",
		"toast.notify_unavailable": "Questo interruttore di notifica non è disponibile.",
		"toast.setting_failed": "Impossibile modificare l'impostazione.",
		"toast.setting_saved": "Impostazione salvata.",
		"toast.name_required": "Inserisci un nome.",
		"toast.value_invalid": "Inserisci un valore valido.",
		"banner.stale": "I dati in tempo reale non sono disponibili. Questi sono gli ultimi valori rilevati; i comandi da remoto sono disabilitati.",
		"banner.offline.title": "Offline.",
		"banner.offline.text": "Questo generatore non è raggiungibile; i dati in tempo reale potrebbero non essere aggiornati e le azioni da remoto non sono disponibili.",
		"banner.estop.title": "Arresto di emergenza inserito.",
		"banner.estop.text": "L'avvio e la prova periodica da remoto sono disabilitati finché non viene ripristinato sul generatore.",
		"banner.fault.title": "Guasto critico.",
		"banner.outage.title": "Casa alimentata dal generatore.",
		"banner.outage.text": "L'alimentazione di rete è assente.",
		"status.offline": "Offline",
		"status.estop": "Arresto di emergenza",
		"status.fault": "Guasto",
		"status.exercising": "In prova periodica",
		"status.running": "In funzione",
		"status.running_outage": "In funzione — blackout",
		"status.ready": "Pronto all'avvio",
		"status.standby": "In attesa",
		"image.alt": "Generatore {model}",
		"image.representative": "Immagine rappresentativa del prodotto",
		"flow.utility": "Rete elettrica",
		"flow.home": "Casa",
		"flow.out": "Assente",
		"stat.engine": "Motore",
		"stat.load": "Carico",
		"stat.speed": "Velocità",
		"stat.frequency": "Frequenza",
		"stat.battery": "Batteria",
		"stat.oil_pressure": "Pressione dell'olio",
		"stat.coolant": "Refrigerante",
		"stat.fuel": "Carburante",
		"stat.total_runtime": "Ore totali",
		"unit.rpm": "giri/min",
		"tab.overview": "Panoramica",
		"tab.controls": "Comandi",
		"tab.activity": "Attività",
		"tab.maintenance": "Manutenzione",
		"tab.profile": "Profilo",
		"tab.diagnostics": "Diagnostica",
		"field.mode": "Modalità",
		"field.frequency": "Frequenza",
		"field.duration": "Durata",
		"overview.status": "Stato",
		"overview.state": "Stato operativo",
		"overview.mode_switch": "Selettore di modalità",
		"overview.power_source": "Fonte di alimentazione",
		"overview.last_run": "Ultimo funzionamento",
		"overview.active_alerts": "Allarmi attivi",
		"overview.shutdown_reason": "Motivo dell'arresto",
		"overview.next_exercise": "Prossima prova periodica",
		"overview.when": "Quando",
		"overview.last_exercise": "Ultima prova periodica",
		"overview.no_schedule": "Nessuna prova periodica pianificata. Impostane una nella scheda Comandi.",
		"alert.critical": "critico",
		"controls.remote_exercise": "Prova periodica da remoto",
		"controls.start": "Avvia prova periodica ora",
		"controls.stop": "Interrompi prova periodica",
		"controls.start_hint": "L'avvio è disponibile solo quando il generatore è in Auto e pronto all'avvio (stato attuale: {status}).",
		"controls.schedule": "Pianificazione della prova periodica",
		"controls.create_schedule": "Crea una pianificazione",
		"controls.duration_minutes": "Durata (minuti)",
		"controls.next_start": "Prossimo avvio",
		"controls.save_schedule": "Salva pianificazione",
		"controls.delete_schedule": "Elimina pianificazione",
		"controls.no_scheduling": "La pianificazione da remoto della prova periodica non è disponibile per questa centralina.",
		"controls.controller": "Centralina",
		"controls.sync_clock": "Sincronizza orologio della centralina",
		"controls.controller_clock": "Orologio della centralina: {time}",
		"controls.add_note": "Aggiungi una nota di manutenzione",
		"controls.note_label": "Nota di manutenzione",
		"controls.note_placeholder": "Che cosa è stato fatto…",
		"controls.add_note_button": "Aggiungi nota",
		"controls.notifications": "Notifiche (account)",
		"confirm.start.title": "Avviare subito una prova periodica?",
		"confirm.start.text": "Il motore del generatore si avvierà ed eseguirà la prova periodica.",
		"confirm.start.action": "Avvia prova periodica",
		"confirm.delete.title": "Eliminare la pianificazione della prova periodica?",
		"confirm.delete.text": "Il generatore non eseguirà automaticamente la prova periodica finché non crei una nuova pianificazione.",
		"confirm.delete.action": "Elimina pianificazione",
		"activity.log": "Registro attività",
		"activity.none": "Nessuna attività registrata.",
		"activity.notifications": "Notifiche",
		"activity.no_notifications": "Nessuna notifica.",
		"activity.estop": "Arresto di emergenza",
		"activity.fmi": "FMI {value}",
		"maintenance.title": "Manutenzione",
		"maintenance.last": "Ultima manutenzione",
		"maintenance.next": "Prossima manutenzione",
		"maintenance.interval": "Intervallo",
		"maintenance.runtime_since": "Ore dall'ultima manutenzione",
		"maintenance.history": "Storico",
		"maintenance.none": "Ancora nessuna nota di manutenzione. Aggiungine una nella scheda Comandi.",
		"maintenance.dealer": "Rivenditore",
		"maintenance.homeowner": "Proprietario",
		"profile.model": "Modello",
		"profile.serial": "Numero di serie",
		"profile.controller": "Centralina",
		"profile.firmware": "Firmware",
		"profile.fuel": "Carburante",
		"profile.cooling": "Raffreddamento",
		"profile.rated_voltage": "Tensione nominale",
		"profile.site": "Installazione e assistenza",
		"profile.address": "Indirizzo",
		"profile.connection": "Connessione",
		"profile.service_agreement": "Contratto di assistenza",
		"profile.term": "Durata",
		"profile.dealer": "Rivenditore",
		"profile.dealer_phone": "Telefono del rivenditore",
		"profile.load_module": "Modulo di distacco carichi",
		"profile.pim": "Modulo di interfaccia programmabile (PIM)",
		"profile.transfer_switch": "Commutatore di trasferimento",
		"profile.connected": "connesso",
		"profile.offline": "offline",
		"profile.no_parameters": "Nessun parametro segnalato.",
		"profile.position": "Posizione",
		"profile.edit": "Modifica {name}",
		"edit.title": "Modifica impostazione",
		"edit.name": "Nome",
		"edit.value": "Valore",
		"edit.save": "Salva",
		"diagnostics.title": "Diagnostica",
		"diagnostics.connected": "Connesso",
		"diagnostics.device_ip": "Indirizzo IP visto da Rehlko",
		"diagnostics.mac": "Indirizzo MAC",
		"diagnostics.uptime": "Disponibilità della connessione",
		"diagnostics.last_connected": "Ultima connessione",
		"diagnostics.parameters_updated": "Aggiornamento dei parametri",
		"diagnostics.cellular_status": "Stato dei dati cellulare",
		"diagnostics.cellular_used": "Dati cellulare utilizzati",
		"diagnostics.auto_update": "Aggiornamenti firmware automatici",
		"diagnostics.details_refreshed": "Aggiornamento dei dettagli",
		"diagnostics.feeds_refreshed": "Aggiornamento dei feed",
		"diagnostics.account": "Account",
		"diagnostics.account_ok": "OK",
		"diagnostics.account_failed": "Ultimo polling non riuscito",
		"diagnostics.entities": "Entità",
		"diagnostics.entities_text": "Questo generatore è rappresentato da {count} entità di Home Assistant (sensori, controlli e diagnostica). La pagina del dispositivo contiene l'elenco completo e il relativo storico.",
		"diagnostics.open_device": "Apri pagina del dispositivo"
	},
	"./locales/ja.json": {
		"common.generator": "発電機",
		"common.open_sidebar": "サイドバーを開く",
		"common.refresh": "更新",
		"common.cancel": "キャンセル",
		"common.yes": "はい",
		"common.no": "いいえ",
		"common.on": "オン",
		"common.off": "オフ",
		"common.unknown": "不明",
		"common.show_more": "さらに表示",
		"connection.failed": "Rehlko 統合に接続できません。",
		"connection.retrying": "接続を再試行しています…",
		"empty.connecting": "統合に接続しています…",
		"empty.unavailable": "発電機のデータを取得できません。Home Assistant の管理者としてサインインし、統合の状態を確認してください。",
		"empty.not_loaded": "Rehlko アカウントが読み込まれていません。「設定」→「デバイスとサービス」で接続エラーやサインインエラーがないか確認してください。",
		"empty.no_generators": "Rehlko アカウントに発電機がまだ見つかりません。統合の読み込みが完了すると、ここに表示されます。",
		"empty.no_integration": "発電機をここに表示するには、「設定」→「デバイスとサービス」で Rehlko Energy Management 統合を追加してください。",
		"empty.open_integrations": "デバイスとサービスを開く",
		"toast.no_device": "この発電機にはまだ Home Assistant デバイスがありません。",
		"toast.failed": "リクエストに失敗しました。",
		"toast.refreshed": "更新しました。",
		"toast.exercise_started": "試運転の開始をリクエストしました。",
		"toast.exercise_stopped": "試運転の停止をリクエストしました。",
		"toast.schedule_saved": "スケジュールを保存しました。",
		"toast.schedule_deleted": "スケジュールを削除しました。",
		"toast.clock_synced": "コントローラーの時計を設定しました。",
		"toast.note_added": "メンテナンスメモを追加しました。",
		"toast.invalid_next_start": "有効な次回の開始日時を入力してください。",
		"toast.note_required": "先にメモを入力してください。",
		"toast.notify_unavailable": "その通知スイッチは利用できません。",
		"toast.setting_failed": "設定を変更できませんでした。",
		"toast.setting_saved": "設定を保存しました。",
		"toast.name_required": "名前を入力してください。",
		"toast.value_invalid": "有効な値を入力してください。",
		"banner.stale": "ライブデータを取得できません。表示されているのは最後に報告された値で、リモート操作は無効になっています。",
		"banner.offline.title": "オフラインです。",
		"banner.offline.text": "この発電機に接続できません。ライブデータが古い可能性があり、リモート操作は利用できません。",
		"banner.estop.title": "非常停止が作動しています。",
		"banner.estop.text": "発電機本体でリセットするまで、リモート始動と試運転は無効になります。",
		"banner.fault.title": "重大な故障が発生しています。",
		"banner.outage.title": "発電機から給電しています。",
		"banner.outage.text": "商用電源が停電しています。",
		"status.offline": "オフライン",
		"status.estop": "非常停止",
		"status.fault": "故障",
		"status.exercising": "試運転中",
		"status.running": "運転中",
		"status.running_outage": "運転中（停電）",
		"status.ready": "運転準備完了",
		"status.standby": "待機中",
		"image.alt": "{model} 発電機",
		"image.representative": "製品イメージ画像",
		"flow.utility": "商用電源",
		"flow.home": "ホーム",
		"flow.out": "停電",
		"stat.engine": "エンジン",
		"stat.load": "負荷",
		"stat.speed": "回転数",
		"stat.frequency": "周波数",
		"stat.battery": "バッテリー",
		"stat.oil_pressure": "油圧",
		"stat.coolant": "冷却水",
		"stat.fuel": "燃料",
		"stat.total_runtime": "総運転時間",
		"unit.rpm": "rpm",
		"tab.overview": "概要",
		"tab.controls": "コントロール",
		"tab.activity": "アクティビティ",
		"tab.maintenance": "メンテナンス",
		"tab.profile": "プロファイル",
		"tab.diagnostics": "診断",
		"field.mode": "モード",
		"field.frequency": "頻度",
		"field.duration": "継続時間",
		"overview.status": "ステータス",
		"overview.state": "状態",
		"overview.mode_switch": "モードスイッチ",
		"overview.power_source": "電源",
		"overview.last_run": "前回の運転",
		"overview.active_alerts": "発生中のアラート",
		"overview.shutdown_reason": "シャットダウン原因",
		"overview.next_exercise": "次回の試運転",
		"overview.when": "日時",
		"overview.last_exercise": "前回の試運転",
		"overview.no_schedule": "試運転は予定されていません。「コントロール」タブで設定してください。",
		"alert.critical": "重大",
		"controls.remote_exercise": "リモート試運転",
		"controls.start": "今すぐ試運転を開始",
		"controls.stop": "試運転を停止",
		"controls.start_hint": "試運転を開始できるのは、発電機が Auto で運転準備完了のときのみです（現在：{status}）。",
		"controls.schedule": "試運転スケジュール",
		"controls.create_schedule": "スケジュールを作成",
		"controls.duration_minutes": "継続時間（分）",
		"controls.next_start": "次回の開始日時",
		"controls.save_schedule": "スケジュールを保存",
		"controls.delete_schedule": "スケジュールを削除",
		"controls.no_scheduling": "このコントローラーでは、試運転スケジュールのリモート設定を利用できません。",
		"controls.controller": "コントローラー",
		"controls.sync_clock": "コントローラー時計を同期",
		"controls.controller_clock": "コントローラー時計：{time}",
		"controls.add_note": "メンテナンスメモを追加",
		"controls.note_label": "メンテナンスメモ",
		"controls.note_placeholder": "実施した内容…",
		"controls.add_note_button": "メモを追加",
		"controls.notifications": "通知（アカウント）",
		"confirm.start.title": "今すぐ試運転を開始しますか？",
		"confirm.start.text": "発電機のエンジンが始動し、試運転を行います。",
		"confirm.start.action": "試運転を開始",
		"confirm.delete.title": "試運転スケジュールを削除しますか？",
		"confirm.delete.text": "新しいスケジュールを作成するまで、発電機は自動で試運転を行いません。",
		"confirm.delete.action": "スケジュールを削除",
		"activity.log": "アクティビティログ",
		"activity.none": "アクティビティの記録はありません。",
		"activity.notifications": "通知",
		"activity.no_notifications": "通知はありません。",
		"activity.estop": "非常停止",
		"activity.fmi": "FMI {value}",
		"maintenance.title": "メンテナンス",
		"maintenance.last": "前回のメンテナンス",
		"maintenance.next": "次回のメンテナンス",
		"maintenance.interval": "間隔",
		"maintenance.runtime_since": "メンテナンス後の運転時間",
		"maintenance.history": "履歴",
		"maintenance.none": "メンテナンスメモはまだありません。「コントロール」タブで追加してください。",
		"maintenance.dealer": "販売店",
		"maintenance.homeowner": "所有者",
		"profile.model": "モデル",
		"profile.serial": "シリアル番号",
		"profile.controller": "コントローラー",
		"profile.firmware": "ファームウェア",
		"profile.fuel": "燃料",
		"profile.cooling": "冷却方式",
		"profile.rated_voltage": "定格電圧",
		"profile.site": "設置場所とサービス",
		"profile.address": "住所",
		"profile.connection": "接続方式",
		"profile.service_agreement": "保守契約",
		"profile.term": "契約期間",
		"profile.dealer": "販売店",
		"profile.dealer_phone": "販売店の電話番号",
		"profile.load_module": "負荷制御モジュール",
		"profile.pim": "プログラマブルインターフェースモジュール",
		"profile.transfer_switch": "切替スイッチ",
		"profile.connected": "接続済み",
		"profile.offline": "オフライン",
		"profile.no_parameters": "報告されたパラメーターはありません。",
		"profile.position": "位置",
		"profile.edit": "{name} を編集",
		"edit.title": "設定を編集",
		"edit.name": "名前",
		"edit.value": "値",
		"edit.save": "保存",
		"diagnostics.title": "診断",
		"diagnostics.connected": "接続済み",
		"diagnostics.device_ip": "Rehlko 側から見た IP アドレス",
		"diagnostics.mac": "MAC アドレス",
		"diagnostics.uptime": "稼働率",
		"diagnostics.last_connected": "最終接続",
		"diagnostics.parameters_updated": "パラメーター最終更新",
		"diagnostics.cellular_status": "セルラーの状態",
		"diagnostics.cellular_used": "セルラーデータ使用量",
		"diagnostics.auto_update": "ファームウェア自動アップデート",
		"diagnostics.details_refreshed": "詳細の最終更新",
		"diagnostics.feeds_refreshed": "フィードの最終更新",
		"diagnostics.account": "アカウント",
		"diagnostics.account_ok": "正常",
		"diagnostics.account_failed": "前回のポーリングに失敗",
		"diagnostics.entities": "エンティティ",
		"diagnostics.entities_text": "この発電機には {count} 個の Home Assistant エンティティ（センサー、コントロール、診断）があります。すべての一覧と履歴はデバイスページで確認できます。",
		"diagnostics.open_device": "デバイスページを開く"
	},
	"./locales/nl.json": {
		"common.generator": "Generator",
		"common.open_sidebar": "Zijbalk openen",
		"common.refresh": "Vernieuwen",
		"common.cancel": "Annuleren",
		"common.yes": "Ja",
		"common.no": "Nee",
		"common.on": "Aan",
		"common.off": "Uit",
		"common.unknown": "onbekend",
		"common.show_more": "Meer tonen",
		"connection.failed": "Kan geen verbinding maken met de Rehlko-integratie.",
		"connection.retrying": "Opnieuw verbinden…",
		"empty.connecting": "Verbinden met de integratie…",
		"empty.unavailable": "Generatorgegevens zijn niet beschikbaar. Log in als Home Assistant-beheerder en controleer de status van de integratie.",
		"empty.not_loaded": "Het Rehlko-account is niet geladen. Controleer bij Instellingen → Apparaten & diensten of er verbindings- of inlogfouten zijn.",
		"empty.no_generators": "Er zijn nog geen generatoren gevonden in je Rehlko-account. Ze verschijnen hier zodra de integratie klaar is met laden.",
		"empty.no_integration": "Voeg de integratie Rehlko Energy Management toe via Instellingen → Apparaten & diensten om je generator hier te zien.",
		"empty.open_integrations": "Apparaten & diensten openen",
		"toast.no_device": "Deze generator heeft nog geen Home Assistant-apparaat.",
		"toast.failed": "Het verzoek is mislukt.",
		"toast.refreshed": "Vernieuwd.",
		"toast.exercise_started": "Start van testrun aangevraagd.",
		"toast.exercise_stopped": "Stoppen van testrun aangevraagd.",
		"toast.schedule_saved": "Schema opgeslagen.",
		"toast.schedule_deleted": "Schema verwijderd.",
		"toast.clock_synced": "Controllerklok ingesteld.",
		"toast.note_added": "Onderhoudsnotitie toegevoegd.",
		"toast.invalid_next_start": "Voer een geldige volgende starttijd in.",
		"toast.note_required": "Typ eerst een notitie.",
		"toast.notify_unavailable": "Die notificatieschakelaar is niet beschikbaar.",
		"toast.setting_failed": "Kan de instelling niet wijzigen.",
		"toast.setting_saved": "Instelling opgeslagen.",
		"toast.name_required": "Voer een naam in.",
		"toast.value_invalid": "Voer een geldige waarde in.",
		"banner.stale": "Live gegevens zijn niet beschikbaar. Dit zijn de laatst gemelde meetwaarden; bediening op afstand is uitgeschakeld.",
		"banner.offline.title": "Offline.",
		"banner.offline.text": "Deze generator is niet bereikbaar; live gegevens kunnen verouderd zijn en acties op afstand zijn niet beschikbaar.",
		"banner.estop.title": "Noodstop geactiveerd.",
		"banner.estop.text": "Starten op afstand en testruns op afstand zijn uitgeschakeld totdat de noodstop bij de generator is gereset.",
		"banner.fault.title": "Kritieke storing.",
		"banner.outage.title": "Draait op generatorstroom.",
		"banner.outage.text": "De netstroom is uitgevallen.",
		"status.offline": "Offline",
		"status.estop": "Noodstop",
		"status.fault": "Storing",
		"status.exercising": "Testrun actief",
		"status.running": "Draait",
		"status.running_outage": "Draait — stroomuitval",
		"status.ready": "Bedrijfsklaar",
		"status.standby": "Stand-by",
		"image.alt": "Generator {model}",
		"image.representative": "Productafbeelding ter illustratie",
		"flow.utility": "Net",
		"flow.home": "Woning",
		"flow.out": "Uitgevallen",
		"stat.engine": "Motor",
		"stat.load": "Belasting",
		"stat.speed": "Toerental",
		"stat.frequency": "Frequentie",
		"stat.battery": "Accu",
		"stat.oil_pressure": "Oliedruk",
		"stat.coolant": "Koelvloeistof",
		"stat.fuel": "Brandstof",
		"stat.total_runtime": "Totale draaitijd",
		"unit.rpm": "tpm",
		"tab.overview": "Overzicht",
		"tab.controls": "Bediening",
		"tab.activity": "Activiteit",
		"tab.maintenance": "Onderhoud",
		"tab.profile": "Profiel",
		"tab.diagnostics": "Diagnostiek",
		"field.mode": "Modus",
		"field.frequency": "Frequentie",
		"field.duration": "Duur",
		"overview.status": "Status",
		"overview.state": "Toestand",
		"overview.mode_switch": "Modusschakelaar",
		"overview.power_source": "Stroombron",
		"overview.last_run": "Laatst gedraaid",
		"overview.active_alerts": "Actieve alarmen",
		"overview.shutdown_reason": "Reden van uitschakeling",
		"overview.next_exercise": "Volgende testrun",
		"overview.when": "Wanneer",
		"overview.last_exercise": "Laatste testrun",
		"overview.no_schedule": "Geen testrun gepland. Stel er een in op het tabblad Bediening.",
		"alert.critical": "kritiek",
		"controls.remote_exercise": "Testrun op afstand",
		"controls.start": "Testrun nu starten",
		"controls.stop": "Testrun stoppen",
		"controls.start_hint": "Starten is alleen mogelijk wanneer de generator in Auto staat en bedrijfsklaar is (nu: {status}).",
		"controls.schedule": "Testrunschema",
		"controls.create_schedule": "Schema aanmaken",
		"controls.duration_minutes": "Duur (minuten)",
		"controls.next_start": "Volgende start",
		"controls.save_schedule": "Schema opslaan",
		"controls.delete_schedule": "Schema verwijderen",
		"controls.no_scheduling": "Testruns op afstand plannen is niet beschikbaar voor deze controller.",
		"controls.controller": "Controller",
		"controls.sync_clock": "Controllerklok synchroniseren",
		"controls.controller_clock": "Controllerklok: {time}",
		"controls.add_note": "Onderhoudsnotitie toevoegen",
		"controls.note_label": "Onderhoudsnotitie",
		"controls.note_placeholder": "Wat er is gedaan…",
		"controls.add_note_button": "Notitie toevoegen",
		"controls.notifications": "Notificaties (account)",
		"confirm.start.title": "Nu een testrun starten?",
		"confirm.start.text": "De motor van de generator start en voert de testrun uit.",
		"confirm.start.action": "Testrun starten",
		"confirm.delete.title": "Het testrunschema verwijderen?",
		"confirm.delete.text": "De generator voert geen automatische testruns meer uit totdat je een nieuw schema aanmaakt.",
		"confirm.delete.action": "Schema verwijderen",
		"activity.log": "Activiteitenlogboek",
		"activity.none": "Geen activiteit geregistreerd.",
		"activity.notifications": "Notificaties",
		"activity.no_notifications": "Geen notificaties.",
		"activity.estop": "Noodstop",
		"activity.fmi": "FMI {value}",
		"maintenance.title": "Onderhoud",
		"maintenance.last": "Laatste onderhoud",
		"maintenance.next": "Volgend onderhoud",
		"maintenance.interval": "Interval",
		"maintenance.runtime_since": "Draaitijd sinds onderhoud",
		"maintenance.history": "Geschiedenis",
		"maintenance.none": "Nog geen onderhoudsnotities. Voeg er een toe op het tabblad Bediening.",
		"maintenance.dealer": "Dealer",
		"maintenance.homeowner": "Huiseigenaar",
		"profile.model": "Model",
		"profile.serial": "Serienummer",
		"profile.controller": "Controller",
		"profile.firmware": "Firmware",
		"profile.fuel": "Brandstof",
		"profile.cooling": "Koeling",
		"profile.rated_voltage": "Nominale spanning",
		"profile.site": "Locatie & service",
		"profile.address": "Adres",
		"profile.connection": "Verbinding",
		"profile.service_agreement": "Servicecontract",
		"profile.term": "Looptijd",
		"profile.dealer": "Dealer",
		"profile.dealer_phone": "Telefoon dealer",
		"profile.load_module": "Lastafschakelmodule",
		"profile.pim": "Programmeerbare interfacemodule",
		"profile.transfer_switch": "Omschakelaar",
		"profile.connected": "verbonden",
		"profile.offline": "offline",
		"profile.no_parameters": "Geen parameters gemeld.",
		"profile.position": "Stand",
		"profile.edit": "{name} bewerken",
		"edit.title": "Instelling bewerken",
		"edit.name": "Naam",
		"edit.value": "Waarde",
		"edit.save": "Opslaan",
		"diagnostics.title": "Diagnostiek",
		"diagnostics.connected": "Verbonden",
		"diagnostics.device_ip": "IP-adres gezien door Rehlko",
		"diagnostics.mac": "MAC-adres",
		"diagnostics.uptime": "Uptime",
		"diagnostics.last_connected": "Laatst verbonden",
		"diagnostics.parameters_updated": "Parameters bijgewerkt",
		"diagnostics.cellular_status": "Status mobiele data",
		"diagnostics.cellular_used": "Verbruikte mobiele data",
		"diagnostics.auto_update": "Automatische firmware-updates",
		"diagnostics.details_refreshed": "Details vernieuwd",
		"diagnostics.feeds_refreshed": "Feeds vernieuwd",
		"diagnostics.account": "Account",
		"diagnostics.account_ok": "OK",
		"diagnostics.account_failed": "Laatste ophaalpoging mislukt",
		"diagnostics.entities": "Entiteiten",
		"diagnostics.entities_text": "Deze generator heeft {count} Home Assistant-entiteiten (sensoren, bediening en diagnostiek). Op de apparaatpagina vind je de volledige lijst met hun geschiedenis.",
		"diagnostics.open_device": "Apparaatpagina openen"
	},
	"./locales/pl.json": {
		"common.generator": "Agregat",
		"common.open_sidebar": "Otwórz pasek boczny",
		"common.refresh": "Odśwież",
		"common.cancel": "Anuluj",
		"common.yes": "Tak",
		"common.no": "Nie",
		"common.on": "Wł.",
		"common.off": "Wył.",
		"common.unknown": "nieznany",
		"common.show_more": "Pokaż więcej",
		"connection.failed": "Nie można połączyć się z integracją Rehlko.",
		"connection.retrying": "Ponawianie połączenia…",
		"empty.connecting": "Łączenie z integracją…",
		"empty.unavailable": "Dane agregatu są niedostępne. Zaloguj się jako administrator Home Assistant i sprawdź stan integracji.",
		"empty.not_loaded": "Konto Rehlko nie jest załadowane. Sprawdź w menu Ustawienia → Urządzenia oraz usługi, czy nie występują błędy połączenia lub logowania.",
		"empty.no_generators": "Na Twoim koncie Rehlko nie znaleziono jeszcze żadnych agregatów. Pojawią się tutaj, gdy integracja zakończy ładowanie.",
		"empty.no_integration": "Dodaj integrację Rehlko Energy Management w menu Ustawienia → Urządzenia oraz usługi, aby zobaczyć tutaj swój agregat.",
		"empty.open_integrations": "Otwórz Urządzenia oraz usługi",
		"toast.no_device": "Ten agregat nie ma jeszcze urządzenia w Home Assistant.",
		"toast.failed": "Żądanie nie powiodło się.",
		"toast.refreshed": "Odświeżono.",
		"toast.exercise_started": "Zażądano rozpoczęcia rozruchu testowego.",
		"toast.exercise_stopped": "Zażądano zatrzymania rozruchu testowego.",
		"toast.schedule_saved": "Zapisano harmonogram.",
		"toast.schedule_deleted": "Usunięto harmonogram.",
		"toast.clock_synced": "Ustawiono zegar sterownika.",
		"toast.note_added": "Dodano notatkę z konserwacji.",
		"toast.invalid_next_start": "Podaj prawidłowy czas następnego startu.",
		"toast.note_required": "Najpierw wpisz notatkę.",
		"toast.notify_unavailable": "Ten przełącznik powiadomień jest niedostępny.",
		"toast.setting_failed": "Nie udało się zmienić ustawienia.",
		"toast.setting_saved": "Ustawienie zapisane.",
		"toast.name_required": "Wpisz nazwę.",
		"toast.value_invalid": "Wpisz prawidłową wartość.",
		"banner.stale": "Bieżące dane są niedostępne. Wyświetlane są ostatnie zgłoszone odczyty; zdalne sterowanie jest wyłączone.",
		"banner.offline.title": "Offline.",
		"banner.offline.text": "Ten agregat jest nieosiągalny; bieżące dane mogą być nieaktualne, a zdalne akcje są niedostępne.",
		"banner.estop.title": "Aktywne zatrzymanie awaryjne.",
		"banner.estop.text": "Zdalne uruchamianie i rozruch testowy są zablokowane do czasu jego zresetowania przy agregacie.",
		"banner.fault.title": "Usterka krytyczna.",
		"banner.outage.title": "Zasilanie z agregatu.",
		"banner.outage.text": "Brak zasilania sieciowego.",
		"status.offline": "Offline",
		"status.estop": "Zatrzymanie awaryjne",
		"status.fault": "Usterka",
		"status.exercising": "Rozruch testowy",
		"status.running": "Praca",
		"status.running_outage": "Praca – zanik zasilania",
		"status.ready": "Gotowość do pracy",
		"status.standby": "Gotowość",
		"image.alt": "Agregat {model}",
		"image.representative": "Poglądowe zdjęcie produktu",
		"flow.utility": "Sieć",
		"flow.home": "Dom",
		"flow.out": "Zanik",
		"stat.engine": "Silnik",
		"stat.load": "Obciążenie",
		"stat.speed": "Obroty",
		"stat.frequency": "Częstotliwość",
		"stat.battery": "Akumulator",
		"stat.oil_pressure": "Ciśnienie oleju",
		"stat.coolant": "Płyn chłodzący",
		"stat.fuel": "Paliwo",
		"stat.total_runtime": "Łączny czas pracy",
		"unit.rpm": "obr./min",
		"tab.overview": "Przegląd",
		"tab.controls": "Sterowanie",
		"tab.activity": "Aktywność",
		"tab.maintenance": "Konserwacja",
		"tab.profile": "Profil",
		"tab.diagnostics": "Diagnostyka",
		"field.mode": "Tryb",
		"field.frequency": "Częstotliwość",
		"field.duration": "Czas trwania",
		"overview.status": "Status",
		"overview.state": "Stan",
		"overview.mode_switch": "Przełącznik trybu",
		"overview.power_source": "Źródło zasilania",
		"overview.last_run": "Ostatnie uruchomienie",
		"overview.active_alerts": "Aktywne alerty",
		"overview.shutdown_reason": "Przyczyna wyłączenia awaryjnego",
		"overview.next_exercise": "Następny rozruch testowy",
		"overview.when": "Termin",
		"overview.last_exercise": "Ostatni rozruch testowy",
		"overview.no_schedule": "Brak zaplanowanego rozruchu testowego. Ustaw go na karcie Sterowanie.",
		"alert.critical": "krytyczny",
		"controls.remote_exercise": "Zdalny rozruch testowy",
		"controls.start": "Rozpocznij rozruch testowy teraz",
		"controls.stop": "Zatrzymaj rozruch testowy",
		"controls.start_hint": "Rozpoczęcie jest możliwe tylko wtedy, gdy agregat jest w trybie Auto i gotowy do pracy (teraz: {status}).",
		"controls.schedule": "Harmonogram rozruchów testowych",
		"controls.create_schedule": "Utwórz harmonogram",
		"controls.duration_minutes": "Czas trwania (minuty)",
		"controls.next_start": "Następny start",
		"controls.save_schedule": "Zapisz harmonogram",
		"controls.delete_schedule": "Usuń harmonogram",
		"controls.no_scheduling": "Zdalne planowanie rozruchów testowych nie jest dostępne dla tego sterownika.",
		"controls.controller": "Sterownik",
		"controls.sync_clock": "Synchronizuj zegar sterownika",
		"controls.controller_clock": "Zegar sterownika: {time}",
		"controls.add_note": "Dodaj notatkę z konserwacji",
		"controls.note_label": "Notatka z konserwacji",
		"controls.note_placeholder": "Co zostało zrobione…",
		"controls.add_note_button": "Dodaj notatkę",
		"controls.notifications": "Powiadomienia (konto)",
		"confirm.start.title": "Rozpocząć rozruch testowy teraz?",
		"confirm.start.text": "Silnik agregatu uruchomi się i wykona rozruch testowy.",
		"confirm.start.action": "Rozpocznij rozruch testowy",
		"confirm.delete.title": "Usunąć harmonogram rozruchów testowych?",
		"confirm.delete.text": "Agregat nie będzie automatycznie wykonywał rozruchów testowych, dopóki nie utworzysz nowego harmonogramu.",
		"confirm.delete.action": "Usuń harmonogram",
		"activity.log": "Dziennik aktywności",
		"activity.none": "Brak zarejestrowanej aktywności.",
		"activity.notifications": "Powiadomienia",
		"activity.no_notifications": "Brak powiadomień.",
		"activity.estop": "Zatrzymanie awaryjne",
		"activity.fmi": "FMI {value}",
		"maintenance.title": "Konserwacja",
		"maintenance.last": "Ostatnia konserwacja",
		"maintenance.next": "Następna konserwacja",
		"maintenance.interval": "Interwał",
		"maintenance.runtime_since": "Czas pracy od konserwacji",
		"maintenance.history": "Historia",
		"maintenance.none": "Brak notatek z konserwacji. Dodaj notatkę na karcie Sterowanie.",
		"maintenance.dealer": "Dealer",
		"maintenance.homeowner": "Właściciel",
		"profile.model": "Model",
		"profile.serial": "Numer seryjny",
		"profile.controller": "Sterownik",
		"profile.firmware": "Oprogramowanie układowe",
		"profile.fuel": "Paliwo",
		"profile.cooling": "Chłodzenie",
		"profile.rated_voltage": "Napięcie znamionowe",
		"profile.site": "Miejsce instalacji i serwis",
		"profile.address": "Adres",
		"profile.connection": "Połączenie",
		"profile.service_agreement": "Umowa serwisowa",
		"profile.term": "Okres umowy",
		"profile.dealer": "Dealer",
		"profile.dealer_phone": "Telefon dealera",
		"profile.load_module": "Moduł odciążania",
		"profile.pim": "Programowalny moduł interfejsu",
		"profile.transfer_switch": "Przełącznik zasilania",
		"profile.connected": "połączony",
		"profile.offline": "offline",
		"profile.no_parameters": "Brak zgłoszonych parametrów.",
		"profile.position": "Położenie",
		"profile.edit": "Edytuj: {name}",
		"edit.title": "Edytuj ustawienie",
		"edit.name": "Nazwa",
		"edit.value": "Wartość",
		"edit.save": "Zapisz",
		"diagnostics.title": "Diagnostyka",
		"diagnostics.connected": "Połączony",
		"diagnostics.device_ip": "Adres IP widziany przez Rehlko",
		"diagnostics.mac": "Adres MAC",
		"diagnostics.uptime": "Dostępność połączenia",
		"diagnostics.last_connected": "Ostatnie połączenie",
		"diagnostics.parameters_updated": "Aktualizacja parametrów",
		"diagnostics.cellular_status": "Status sieci komórkowej",
		"diagnostics.cellular_used": "Wykorzystane dane komórkowe",
		"diagnostics.auto_update": "Automatyczne aktualizacje oprogramowania układowego",
		"diagnostics.details_refreshed": "Odświeżenie szczegółów",
		"diagnostics.feeds_refreshed": "Odświeżenie list zdarzeń",
		"diagnostics.account": "Konto",
		"diagnostics.account_ok": "OK",
		"diagnostics.account_failed": "Ostatnie odpytanie nie powiodło się",
		"diagnostics.entities": "Encje",
		"diagnostics.entities_text": "Liczba encji Home Assistant powiązanych z tym agregatem (sensory, sterowanie i diagnostyka): {count}. Pełną listę encji i ich historię znajdziesz na stronie urządzenia.",
		"diagnostics.open_device": "Otwórz stronę urządzenia"
	},
	"./locales/pt-BR.json": {
		"common.generator": "Gerador",
		"common.open_sidebar": "Abrir barra lateral",
		"common.refresh": "Atualizar",
		"common.cancel": "Cancelar",
		"common.yes": "Sim",
		"common.no": "Não",
		"common.on": "Ligado",
		"common.off": "Desligado",
		"common.unknown": "desconhecido",
		"common.show_more": "Mostrar mais",
		"connection.failed": "Não foi possível conectar à integração Rehlko.",
		"connection.retrying": "Tentando conectar novamente…",
		"empty.connecting": "Conectando à integração…",
		"empty.unavailable": "Os dados do gerador estão indisponíveis. Faça login como administrador do Home Assistant e verifique o status da integração.",
		"empty.not_loaded": "A conta Rehlko não está carregada. Verifique em Configurações → Dispositivos & Serviços se há erros de conexão ou de login.",
		"empty.no_generators": "Nenhum gerador encontrado na sua conta Rehlko ainda. Eles aparecem aqui assim que a integração termina de carregar.",
		"empty.no_integration": "Adicione a integração Rehlko Energy Management em Configurações → Dispositivos & Serviços para ver seu gerador aqui.",
		"empty.open_integrations": "Abrir Dispositivos & Serviços",
		"toast.no_device": "Este gerador ainda não tem um dispositivo no Home Assistant.",
		"toast.failed": "A solicitação falhou.",
		"toast.refreshed": "Atualizado.",
		"toast.exercise_started": "Início do exercício solicitado.",
		"toast.exercise_stopped": "Parada do exercício solicitada.",
		"toast.schedule_saved": "Agendamento salvo.",
		"toast.schedule_deleted": "Agendamento excluído.",
		"toast.clock_synced": "Relógio do controlador ajustado.",
		"toast.note_added": "Anotação de manutenção adicionada.",
		"toast.invalid_next_start": "Informe um horário válido para o próximo início.",
		"toast.note_required": "Digite uma anotação primeiro.",
		"toast.notify_unavailable": "Esse interruptor de notificação não está disponível.",
		"toast.setting_failed": "Não foi possível alterar a configuração.",
		"toast.setting_saved": "Configuração salva.",
		"toast.name_required": "Digite um nome.",
		"toast.value_invalid": "Digite um valor válido.",
		"banner.stale": "Os dados em tempo real estão indisponíveis. Estas são as últimas leituras informadas; os controles remotos estão desativados.",
		"banner.offline.title": "Offline.",
		"banner.offline.text": "Este gerador está inacessível; os dados em tempo real podem estar desatualizados e as ações remotas estão indisponíveis.",
		"banner.estop.title": "Parada de emergência acionada.",
		"banner.estop.text": "A partida e o exercício remotos ficam desativados até que ela seja rearmada no gerador.",
		"banner.fault.title": "Falha crítica.",
		"banner.outage.title": "Funcionando com energia do gerador.",
		"banner.outage.text": "A rede elétrica está sem energia.",
		"status.offline": "Offline",
		"status.estop": "Parada de emergência",
		"status.fault": "Falha",
		"status.exercising": "Em exercício",
		"status.running": "Em funcionamento",
		"status.running_outage": "Em funcionamento — falta de energia",
		"status.ready": "Pronto para funcionar",
		"status.standby": "Em espera",
		"image.alt": "Gerador {model}",
		"image.representative": "Imagem ilustrativa do produto",
		"flow.utility": "Rede elétrica",
		"flow.home": "Casa",
		"flow.out": "Sem energia",
		"stat.engine": "Motor",
		"stat.load": "Carga",
		"stat.speed": "Rotação",
		"stat.frequency": "Frequência",
		"stat.battery": "Bateria",
		"stat.oil_pressure": "Pressão do óleo",
		"stat.coolant": "Arrefecimento",
		"stat.fuel": "Combustível",
		"stat.total_runtime": "Funcionamento total",
		"unit.rpm": "rpm",
		"tab.overview": "Visão geral",
		"tab.controls": "Controles",
		"tab.activity": "Atividade",
		"tab.maintenance": "Manutenção",
		"tab.profile": "Perfil",
		"tab.diagnostics": "Diagnóstico",
		"field.mode": "Modo",
		"field.frequency": "Frequência",
		"field.duration": "Duração",
		"overview.status": "Status",
		"overview.state": "Estado",
		"overview.mode_switch": "Chave de modo",
		"overview.power_source": "Fonte de energia",
		"overview.last_run": "Último funcionamento",
		"overview.active_alerts": "Alertas ativos",
		"overview.shutdown_reason": "Motivo do desligamento",
		"overview.next_exercise": "Próximo exercício",
		"overview.when": "Quando",
		"overview.last_exercise": "Último exercício",
		"overview.no_schedule": "Nenhum exercício agendado. Defina um na aba Controles.",
		"alert.critical": "falha crítica",
		"controls.remote_exercise": "Exercício remoto",
		"controls.start": "Iniciar exercício agora",
		"controls.stop": "Parar exercício",
		"controls.start_hint": "O início do exercício só está disponível quando o gerador está no modo Auto e pronto para funcionar (agora: {status}).",
		"controls.schedule": "Agendamento do exercício",
		"controls.create_schedule": "Criar um agendamento",
		"controls.duration_minutes": "Duração (minutos)",
		"controls.next_start": "Próximo início",
		"controls.save_schedule": "Salvar agendamento",
		"controls.delete_schedule": "Excluir agendamento",
		"controls.no_scheduling": "O agendamento remoto de exercícios não está disponível para este controlador.",
		"controls.controller": "Controlador",
		"controls.sync_clock": "Sincronizar relógio do controlador",
		"controls.controller_clock": "Relógio do controlador: {time}",
		"controls.add_note": "Adicionar uma anotação de manutenção",
		"controls.note_label": "Anotação de manutenção",
		"controls.note_placeholder": "O que foi feito…",
		"controls.add_note_button": "Adicionar anotação",
		"controls.notifications": "Notificações (conta)",
		"confirm.start.title": "Iniciar um exercício agora?",
		"confirm.start.text": "O motor do gerador vai dar partida e executar o exercício.",
		"confirm.start.action": "Iniciar exercício",
		"confirm.delete.title": "Excluir o agendamento do exercício?",
		"confirm.delete.text": "O gerador não fará exercícios automaticamente até que você crie um novo agendamento.",
		"confirm.delete.action": "Excluir agendamento",
		"activity.log": "Registro de atividades",
		"activity.none": "Nenhuma atividade registrada.",
		"activity.notifications": "Notificações",
		"activity.no_notifications": "Nenhuma notificação.",
		"activity.estop": "Parada de emergência",
		"activity.fmi": "FMI {value}",
		"maintenance.title": "Manutenção",
		"maintenance.last": "Última manutenção",
		"maintenance.next": "Próxima manutenção",
		"maintenance.interval": "Intervalo",
		"maintenance.runtime_since": "Funcionamento desde a manutenção",
		"maintenance.history": "Histórico",
		"maintenance.none": "Ainda não há anotações de manutenção. Adicione uma na aba Controles.",
		"maintenance.dealer": "Revendedor",
		"maintenance.homeowner": "Proprietário",
		"profile.model": "Modelo",
		"profile.serial": "Número de série",
		"profile.controller": "Controlador",
		"profile.firmware": "Firmware",
		"profile.fuel": "Combustível",
		"profile.cooling": "Arrefecimento",
		"profile.rated_voltage": "Tensão nominal",
		"profile.site": "Local e serviço",
		"profile.address": "Endereço",
		"profile.connection": "Conexão",
		"profile.service_agreement": "Contrato de serviço",
		"profile.term": "Vigência",
		"profile.dealer": "Revendedor",
		"profile.dealer_phone": "Telefone do revendedor",
		"profile.load_module": "Módulo de corte de carga",
		"profile.pim": "Módulo de interface programável",
		"profile.transfer_switch": "Chave de transferência",
		"profile.connected": "online",
		"profile.offline": "offline",
		"profile.no_parameters": "Nenhum parâmetro informado.",
		"profile.position": "Posição",
		"profile.edit": "Editar {name}",
		"edit.title": "Editar configuração",
		"edit.name": "Nome",
		"edit.value": "Valor",
		"edit.save": "Salvar",
		"diagnostics.title": "Diagnóstico",
		"diagnostics.connected": "Conectado",
		"diagnostics.device_ip": "Endereço IP visto pela Rehlko",
		"diagnostics.mac": "Endereço MAC",
		"diagnostics.uptime": "Tempo de atividade",
		"diagnostics.last_connected": "Última conexão",
		"diagnostics.parameters_updated": "Parâmetros atualizados",
		"diagnostics.cellular_status": "Status da rede celular",
		"diagnostics.cellular_used": "Dados móveis usados",
		"diagnostics.auto_update": "Atualizações automáticas de firmware",
		"diagnostics.details_refreshed": "Detalhes atualizados",
		"diagnostics.feeds_refreshed": "Feeds atualizados",
		"diagnostics.account": "Conta",
		"diagnostics.account_ok": "OK",
		"diagnostics.account_failed": "Falha na última consulta",
		"diagnostics.entities": "Entidades",
		"diagnostics.entities_text": "{count} entidades do Home Assistant representam este gerador (sensores, controles e diagnósticos). A página do dispositivo tem a lista completa e o histórico delas.",
		"diagnostics.open_device": "Abrir página do dispositivo"
	},
	"./locales/zh-Hans.json": {
		"common.generator": "发电机",
		"common.open_sidebar": "打开侧边栏",
		"common.refresh": "刷新",
		"common.cancel": "取消",
		"common.yes": "是",
		"common.no": "否",
		"common.on": "开启",
		"common.off": "关闭",
		"common.unknown": "未知",
		"common.show_more": "显示更多",
		"connection.failed": "无法连接到 Rehlko 集成。",
		"connection.retrying": "正在重试连接…",
		"empty.connecting": "正在连接集成…",
		"empty.unavailable": "发电机数据不可用。请以 Home Assistant 管理员身份登录，并检查集成的状态。",
		"empty.not_loaded": "Rehlko 账户未加载。请在“设置 → 设备与服务”中检查是否存在连接或登录错误。",
		"empty.no_generators": "您的 Rehlko 账户下尚未发现发电机。集成加载完成后，发电机会显示在此处。",
		"empty.no_integration": "请在“设置 → 设备与服务”中添加 Rehlko Energy Management 集成，即可在此处查看您的发电机。",
		"empty.open_integrations": "打开“设备与服务”",
		"toast.no_device": "此发电机尚无对应的 Home Assistant 设备。",
		"toast.failed": "请求失败。",
		"toast.refreshed": "已刷新。",
		"toast.exercise_started": "已请求开始试机。",
		"toast.exercise_stopped": "已请求停止试机。",
		"toast.schedule_saved": "计划已保存。",
		"toast.schedule_deleted": "计划已删除。",
		"toast.clock_synced": "控制器时钟已设置。",
		"toast.note_added": "维护备注已添加。",
		"toast.invalid_next_start": "请输入有效的下次开始时间。",
		"toast.note_required": "请先输入备注。",
		"toast.notify_unavailable": "该通知开关不可用。",
		"toast.setting_failed": "无法更改该设置。",
		"toast.setting_saved": "设置已保存。",
		"toast.name_required": "请输入名称。",
		"toast.value_invalid": "请输入有效的值。",
		"banner.stale": "实时数据不可用。以下为最后一次上报的读数；远程控制已禁用。",
		"banner.offline.title": "离线。",
		"banner.offline.text": "无法连接到此发电机；实时数据可能已过时，远程操作不可用。",
		"banner.estop.title": "紧急停机已触发。",
		"banner.estop.text": "在发电机上将其复位之前，远程启动和远程试机已禁用。",
		"banner.fault.title": "严重故障。",
		"banner.outage.title": "正在由发电机供电。",
		"banner.outage.text": "市电已中断。",
		"status.offline": "离线",
		"status.estop": "紧急停机",
		"status.fault": "故障",
		"status.exercising": "试机中",
		"status.running": "运行中",
		"status.running_outage": "运行中（停电）",
		"status.ready": "准备就绪",
		"status.standby": "待机",
		"image.alt": "{model} 发电机",
		"image.representative": "产品示意图",
		"flow.utility": "市电",
		"flow.home": "住宅",
		"flow.out": "中断",
		"stat.engine": "发动机",
		"stat.load": "负载",
		"stat.speed": "转速",
		"stat.frequency": "频率",
		"stat.battery": "电池",
		"stat.oil_pressure": "机油压力",
		"stat.coolant": "冷却液",
		"stat.fuel": "燃料",
		"stat.total_runtime": "总运行时间",
		"unit.rpm": "rpm",
		"tab.overview": "概览",
		"tab.controls": "控制",
		"tab.activity": "活动",
		"tab.maintenance": "维护",
		"tab.profile": "设备信息",
		"tab.diagnostics": "诊断",
		"field.mode": "模式",
		"field.frequency": "频率",
		"field.duration": "时长",
		"overview.status": "状态",
		"overview.state": "当前状态",
		"overview.mode_switch": "模式开关",
		"overview.power_source": "供电来源",
		"overview.last_run": "上次运行",
		"overview.active_alerts": "当前警报",
		"overview.shutdown_reason": "停机原因",
		"overview.next_exercise": "下次试机",
		"overview.when": "时间",
		"overview.last_exercise": "上次试机",
		"overview.no_schedule": "尚未计划试机。请在“控制”标签页中设置。",
		"alert.critical": "严重",
		"controls.remote_exercise": "远程试机",
		"controls.start": "立即开始试机",
		"controls.stop": "停止试机",
		"controls.start_hint": "仅当发电机处于 Auto 模式且准备就绪时才能开始试机（当前：{status}）。",
		"controls.schedule": "试机计划",
		"controls.create_schedule": "创建计划",
		"controls.duration_minutes": "时长（分钟）",
		"controls.next_start": "下次开始时间",
		"controls.save_schedule": "保存计划",
		"controls.delete_schedule": "删除计划",
		"controls.no_scheduling": "此控制器不支持远程设置试机计划。",
		"controls.controller": "控制器",
		"controls.sync_clock": "同步控制器时钟",
		"controls.controller_clock": "控制器时钟：{time}",
		"controls.add_note": "添加维护备注",
		"controls.note_label": "维护备注",
		"controls.note_placeholder": "已完成的工作…",
		"controls.add_note_button": "添加备注",
		"controls.notifications": "通知（账户）",
		"confirm.start.title": "立即开始试机？",
		"confirm.start.text": "发电机的发动机将启动并进行试机。",
		"confirm.start.action": "开始试机",
		"confirm.delete.title": "删除试机计划？",
		"confirm.delete.text": "在您创建新计划之前，发电机不会自动试机。",
		"confirm.delete.action": "删除计划",
		"activity.log": "活动日志",
		"activity.none": "暂无活动记录。",
		"activity.notifications": "通知",
		"activity.no_notifications": "暂无通知。",
		"activity.estop": "急停",
		"activity.fmi": "FMI {value}",
		"maintenance.title": "维护",
		"maintenance.last": "上次维护",
		"maintenance.next": "下次维护",
		"maintenance.interval": "间隔",
		"maintenance.runtime_since": "维护后运行时间",
		"maintenance.history": "历史记录",
		"maintenance.none": "暂无维护备注。请在“控制”标签页中添加。",
		"maintenance.dealer": "经销商",
		"maintenance.homeowner": "业主",
		"profile.model": "型号",
		"profile.serial": "序列号",
		"profile.controller": "控制器",
		"profile.firmware": "固件",
		"profile.fuel": "燃料",
		"profile.cooling": "冷却方式",
		"profile.rated_voltage": "额定电压",
		"profile.site": "安装地点与服务",
		"profile.address": "地址",
		"profile.connection": "连接方式",
		"profile.service_agreement": "服务协议",
		"profile.term": "期限",
		"profile.dealer": "经销商",
		"profile.dealer_phone": "经销商电话",
		"profile.load_module": "负载管理模块",
		"profile.pim": "可编程接口模块（PIM）",
		"profile.transfer_switch": "转换开关",
		"profile.connected": "已连接",
		"profile.offline": "离线",
		"profile.no_parameters": "未报告任何参数。",
		"profile.position": "位置",
		"profile.edit": "编辑 {name}",
		"edit.title": "编辑设置",
		"edit.name": "名称",
		"edit.value": "值",
		"edit.save": "保存",
		"diagnostics.title": "诊断",
		"diagnostics.connected": "已连接",
		"diagnostics.device_ip": "Rehlko 看到的 IP 地址",
		"diagnostics.mac": "MAC 地址",
		"diagnostics.uptime": "在线率",
		"diagnostics.last_connected": "上次连接",
		"diagnostics.parameters_updated": "参数更新时间",
		"diagnostics.cellular_status": "蜂窝数据状态",
		"diagnostics.cellular_used": "已用蜂窝数据",
		"diagnostics.auto_update": "自动固件更新",
		"diagnostics.details_refreshed": "详情刷新时间",
		"diagnostics.feeds_refreshed": "日志与通知刷新时间",
		"diagnostics.account": "账户",
		"diagnostics.account_ok": "正常",
		"diagnostics.account_failed": "上次轮询失败",
		"diagnostics.entities": "实体",
		"diagnostics.entities_text": "此发电机对应 {count} 个 Home Assistant 实体（传感器、控制和诊断）。完整列表及其历史记录可在设备页面查看。",
		"diagnostics.open_device": "打开设备页面"
	}
}), Ft = {};
for (let [e, t] of Object.entries(Pt)) Ft[e.replace(/^.*\/|\.json$/g, "").toLowerCase()] = t;
var It = {
	pt: "pt-br",
	"pt-pt": "pt-br",
	zh: "zh-hans",
	"zh-cn": "zh-hans",
	"zh-sg": "zh-hans"
};
function Lt(e) {
	let t = (e ?? "en").toLowerCase();
	for (let e of [
		t,
		It[t],
		t.split("-")[0]
	]) if (e && Ft[e]) return e;
	return "en";
}
var Rt = /* @__PURE__ */ new Map();
function zt(e) {
	let t = Lt(e), n = Rt.get(t);
	if (!n) {
		let e = Ft[t] ?? {};
		n = (t, n) => {
			let r = e[t] || Nt[t] || t;
			return n ? r.replace(/\{(\w+)\}/g, (e, t) => t in n ? String(n[t]) : e) : r;
		}, Rt.set(t, n);
	}
	return n;
}
// \0@oxc-project+runtime@0.156.0/helpers/esm/decorate.js
function q(e, t, n, r) {
	var i = arguments.length, a = i < 3 ? t : r === null ? r = Object.getOwnPropertyDescriptor(t, n) : r, o;
	if (typeof Reflect == "object" && typeof Reflect.decorate == "function") a = Reflect.decorate(e, t, n, r);
	else for (var s = e.length - 1; s >= 0; s--) (o = e[s]) && (a = (i < 3 ? o(a) : i > 3 ? o(t, n, a) : o(t, n)) || a);
	return i > 3 && a && Object.defineProperty(t, n, a), a;
}
// src/rehlko-energy-panel.ts
var J = [
	"overview",
	"controls",
	"activity",
	"maintenance",
	"profile",
	"diagnostics"
], Bt = [
	"Unloaded",
	"UnloadedFullSpeed",
	"LoadedFullSpeed",
	"EcoExercise"
], Vt = [
	"Weekly",
	"EveryOtherWeek",
	"Monthly"
], Y = 50, X = {
	status: "sensor.status.state",
	engine: "sensor.engine_state.state",
	switchState: "sensor.switch_state.state",
	powerSource: "sensor.power_source.state",
	mode: "select.exercise_mode.state",
	frequency: "select.exercise_frequency.state",
	level: "event.activity.state_attributes.event_type.state",
	notification: "event.notifications.state_attributes.event_type.state",
	fuel: "sensor.fuel_type.state",
	cooling: "sensor.cooling_type.state",
	connection: "sensor.connection_type.state",
	agreement: "sensor.service_agreement_status.state",
	cellular: "sensor.cellular_data_status.state",
	atsPosition: "sensor.ats_power_source.state"
}, Ht = {
	sendShutdowns: "notify_shutdowns",
	sendWarnings: "notify_warnings",
	sendGeneratorRunningNotices: "notify_running",
	sendNotices: "notify_notices",
	sendConnectionNotices: "notify_connection",
	sendMaintenanceNotices: "notify_maintenance",
	sendLongRunningNotices: "notify_long_running",
	sendNotificationEmails: "notify_emails",
	sendPushNotifications: "notify_push"
}, Ut = {
	offline: "status.offline",
	estop: "status.estop",
	fault: "status.fault",
	exercising: "status.exercising"
};
function Z(e) {
	return T`<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d=${e} /></svg>`;
}
function Wt(e, t) {
	return typeof e == "object" && e && "message" in e && typeof e.message == "string" ? e.message : t;
}
function Q(e) {
	return `${e.entry_id}:${e.device_id}`;
}
var $ = class extends P {
	constructor(...e) {
		super(...e), this.narrow = !1, this.snapshot = {
			generators: [],
			accounts: []
		}, this.selected = null, this.tab = "overview", this.busy = !1, this.toast = null, this.connectionError = null, this.receivedSnapshot = !1, this.confirm = null, this.editing = null, this.eventLimit = Y, this.notificationLimit = Y, this.t = zt(), this.fmt = V, this.subscriptionGeneration = 0;
	}
	static {
		this.styles = ot;
	}
	connectedCallback() {
		super.connectedCallback(), this.subscribe();
	}
	disconnectedCallback() {
		super.disconnectedCallback(), this.stopSubscription(), clearTimeout(this.toastTimer);
	}
	shouldUpdate(e) {
		if ([...e.keys()].some((e) => e !== "hass")) return !0;
		let t = e.get("hass"), n = this.hass;
		return t?.connection !== n?.connection || t?.language !== n?.language || t?.locale !== n?.locale || t?.localize !== n?.localize || t?.config !== n?.config || t?.dockedSidebar !== n?.dockedSidebar;
	}
	willUpdate(e) {
		e.has("hass") && (this.t = zt(this.hass?.locale?.language ?? this.hass?.language), this.fmt = bt(this.hass), this.loadEntityTranslations());
	}
	updated(e) {
		e.has("hass") && this.subscribe(), e.has("confirm") && (this.confirm ? this.field("confirm-cancel")?.focus() : this.restoreFocus?.focus()), e.has("editing") && (this.editing ? this.field("edit-name")?.select() : this.restoreFocus?.focus());
	}
	stopSubscription() {
		this.subscriptionGeneration++, this.unsub?.(), this.unsub = void 0, this.subscriptionConnection = void 0, clearTimeout(this.retryTimer);
	}
	async subscribe() {
		if (!this.isConnected || !this.hass || this.subscriptionConnection === this.hass.connection) return;
		this.stopSubscription();
		let e = this.subscriptionGeneration;
		this.subscriptionConnection = this.hass.connection;
		try {
			let t = await this.hass.connection.subscribeMessage((t) => {
				e === this.subscriptionGeneration && this.isConnected && this.onSnapshot(t);
			}, { type: "rehlko_energy/subscribe" });
			if (e !== this.subscriptionGeneration || !this.isConnected) {
				t();
				return;
			}
			this.unsub = t;
		} catch (t) {
			if (e !== this.subscriptionGeneration || !this.isConnected) return;
			this.subscriptionConnection = void 0, this.connectionError = Wt(t, this.t("connection.failed")), this.retryTimer = window.setTimeout(() => {
				this.subscribe();
			}, 5e3);
		}
	}
	onSnapshot(e) {
		let t = new Map(this.snapshot.generators.map((e) => [Q(e), e])), n = {
			accounts: e.accounts,
			generators: e.generators.map((e) => {
				let n = t.get(`${e.entry_id}:${e.device_id}`);
				return {
					...e,
					events: e.events ?? n?.events ?? [],
					notifications: e.notifications ?? n?.notifications ?? [],
					maintenance_notes: e.maintenance_notes ?? n?.maintenance_notes ?? [],
					entities: e.entities ?? n?.entities ?? {}
				};
			})
		};
		this.snapshot = n, this.receivedSnapshot = !0, this.connectionError = null, this.selected !== null && n.generators.some((e) => Q(e) === this.selected) || (this.selected = n.generators[0] ? Q(n.generators[0]) : null);
	}
	get current() {
		return this.snapshot.generators.find((e) => Q(e) === this.selected);
	}
	account(e) {
		return this.snapshot.accounts.find((t) => t.entry_id === e);
	}
	showToast(e, t = !1) {
		this.toast = {
			text: e,
			err: t
		}, clearTimeout(this.toastTimer), this.toastTimer = window.setTimeout(() => this.toast = null, 4e3);
	}
	async call(e, t, n) {
		if (this.busy || !this.hass) return !1;
		let r = this.current;
		if (!r || !r.ha_device_id) return this.showToast(this.t("toast.no_device"), !0), !1;
		this.busy = !0;
		try {
			return await this.hass.callService("rehlko_energy", e, {
				device_id: r.ha_device_id,
				...t
			}), this.showToast(this.t(n)), !0;
		} catch (e) {
			return this.showToast(Wt(e, this.t("toast.failed")), !0), !1;
		} finally {
			this.busy = !1;
		}
	}
	loadEntityTranslations() {
		let e = this.hass, t = e?.language;
		e?.loadBackendTranslation && t && this.translationsFor !== t && (this.translationsFor = t, e.loadBackendTranslation("entity", "rehlko_energy").catch(() => {
			this.translationsFor = void 0;
		}));
	}
	label(e, t) {
		return t == null || t === "" ? "" : this.hass?.localize?.(`component.rehlko_energy.entity.${e}.${z(t)}`) || R(t);
	}
	notifyLabel(e) {
		let t = Ht[e];
		return t && this.hass?.localize?.(`component.rehlko_energy.entity.switch.${t}.name`) || R(e.replace(/^send/, ""));
	}
	render() {
		let e = this.t, t = this.current;
		return T`
      <div class="wrap">
        <header class="bar">
          ${this.narrow || this.hass?.dockedSidebar === "always_hidden" ? T`<button class="icon-button" aria-label=${e("common.open_sidebar")} @click=${this.toggleMenu}>${Z(Qe)}</button>` : D}
          <h1>${t ? t.name : e("common.generator")}</h1>
          ${this.snapshot.generators.length > 1 ? T`<select class="picker" aria-label=${e("common.generator")} @change=${this.onPick}>
                ${this.snapshot.generators.map((e) => T`<option value=${Q(e)} ?selected=${Q(e) === this.selected}>${e.name}</option>`)}
              </select>` : D}
          <button class=${`icon-button ${this.busy ? "spin" : ""}`} title=${e("common.refresh")} aria-label=${e("common.refresh")}
            ?disabled=${this.busy} @click=${this.refresh}>${Z(rt)}</button>
        </header>
        ${this.connectionError ? T`<div class="banner bad" role="alert">${Z(Ye)}<span>${this.connectionError} ${e("connection.retrying")}</span></div>` : D}
        ${t ? Ve(Q(t), this.renderGenerator(t)) : this.renderEmpty()}
      </div>
      ${this.renderConfirm()}
      ${this.renderEdit()}
      ${this.toast ? T`<div role="status" class=${`toast ${this.toast.err ? "err" : ""}`}>${this.toast.text}</div>` : D}
    `;
	}
	renderEmpty() {
		let e = this.t;
		return this.receivedSnapshot ? T`<div class="card empty">
      <p>${this.snapshot.accounts.some((e) => !e.loaded) ? e("empty.not_loaded") : this.snapshot.accounts.length ? e("empty.no_generators") : e("empty.no_integration")}</p>
      ${this.link("/config/integrations/integration/rehlko_energy", e("empty.open_integrations"), "action ghost")}
    </div>` : T`<div class="card empty">${this.connectionError ? e("empty.unavailable") : e("empty.connecting")}</div>`;
	}
	renderGenerator(e) {
		let t = e.derived, n = e.alerts.some((e) => e.isCriticalFault), r = dt({
			...t,
			hasCriticalFault: n
		}), i = mt(e), a = r === "running" || r === "exercising";
		return T`
      ${this.renderBanner(e, n)}
      <div class="hero">
        <div class="card visual" style=${`--chip:${this.chipColor(r)}`}>
          <figure class="generator-product">
            <img class="generator-photo" src=${i.src} alt=${this.t("image.alt", { model: i.description })}
              width=${i.width} height=${i.height} decoding="async" draggable="false" />
            <figcaption>${i.representative ? this.t("image.representative") : i.caption}</figcaption>
          </figure>
          <span class=${`status-chip ${a ? "live" : ""}`}><span class="status-dot"></span>${this.statusText(e, r)}</span>
        </div>
        <div class="card">
          ${this.renderFlow(e)}
          ${this.renderStats(e)}
        </div>
      </div>

      <div class="tabs" role="tablist" @keydown=${this.onTabKey}>
        ${J.map((e) => T`<button role="tab" id=${`tab-${e}`} aria-controls="tabpanel" aria-selected=${this.tab === e}
            tabindex=${this.tab === e ? 0 : -1} @click=${() => this.tab = e}>${this.t(`tab.${e}`)}</button>`)}
      </div>
      <div id="tabpanel" role="tabpanel" aria-labelledby=${`tab-${this.tab}`}>${this.renderTab(e)}</div>
    `;
	}
	renderBanner(e, t) {
		let n = this.t, r = e.derived, i = (e, t, n, r) => T`<div class=${`banner ${e}`} role="status">${Z(t)}<span><strong>${n}</strong> ${r}</span></div>`;
		if (!e.available || this.connectionError) return T`<div class="banner warn" role="status">${Z(Ue)}<span>${n("banner.stale")}</span></div>`;
		if (!r.is_connected) return i("warn", Ye, n("banner.offline.title"), n("banner.offline.text"));
		if (r.e_stop_engaged) return i("bad", qe, n("banner.estop.title"), n("banner.estop.text"));
		if (t) {
			let t = e.alerts.filter((e) => e.isCriticalFault).map((e) => e.name || R(e.deviceEventId)).join(", ");
			return i("bad", We, n("banner.fault.title"), t);
		}
		return r.utility_present === !1 && r.is_running ? i("info", Ze, n("banner.outage.title"), n("banner.outage.text")) : D;
	}
	renderFlow(e) {
		let t = this.t, n = e.derived, r = n.on_generator_power, i = !r && n.utility_present === !0, a = (e) => {
			let t = H(e, this.fmt);
			return t === null ? null : `${t} V`;
		}, o = n.utility_present === !1 ? t("flow.out") : a(e.details.utilityVoltageV) ?? (n.utility_present ? t("common.on") : "—"), s = n.is_running ? a(e.details.generatorVoltageAvgV) ?? t("status.running") : t("status.standby"), c = r ? "Generator" : i ? "Utility" : null;
		return T`<div class="flow">
      <div class=${`node utility ${i ? "active" : ""} ${n.utility_present === !1 ? "down" : ""}`}>
        ${Z(at)}
        <span class="label">${t("flow.utility")}</span>
        <span class="value">${o}</span>
      </div>
      <div class=${`wire utility ${i ? "flowing" : ""}`}></div>
      <div class=${`node home ${r ? "generator" : i ? "utility" : ""} ${c ? "active" : ""}`}>
        ${Z(Ze)}
        <span class="label">${t("flow.home")}</span>
        <span class="value">${c ? this.label(X.powerSource, c) : "—"}</span>
      </div>
      <div class=${`wire generator ${r ? "flowing" : ""}`}></div>
      <div class=${`node generator ${r ? "active" : ""}`}>
        ${Z(Xe)}
        <span class="label">${t("common.generator")}</span>
        <span class="value">${s}</span>
      </div>
    </div>`;
	}
	renderStats(e) {
		let t = this.t, n = this.fmt, r = e.details, i = St(r.engineOilPressurePsi, n), a = xt(r.engineCoolantTempF, n), o = e.derived.is_running ? Ct(e.derived.load_w, n) : null, s = this.label(X.engine, r.engineState), c = [
			[
				"stat.load",
				o?.text,
				o?.unit
			],
			[
				"stat.speed",
				H(r.engineSpeedRpm, n),
				t("unit.rpm")
			],
			[
				"stat.frequency",
				H(r.engineFrequencyHz, n, 1),
				"Hz"
			],
			[
				"stat.battery",
				H(r.batteryVoltageV, n, 1),
				"V"
			],
			[
				"stat.oil_pressure",
				i?.text,
				i?.unit
			],
			[
				"stat.coolant",
				a?.text,
				a?.unit
			],
			[
				"stat.fuel",
				H(r.fuelLevelPercent, n),
				"%"
			],
			[
				"stat.total_runtime",
				H(r.totalRuntimeHours ?? e.device.totalRuntimeHours, n, 1),
				"h"
			]
		];
		return T`<div class="stat-grid">
      ${s ? T`<div class="stat wide"><div class="k">${t("stat.engine")}</div><div class="v">${s}</div></div>` : D}
      ${c.filter(([, e]) => e != null).map(([e, n, r]) => T`<div class="stat"><div class="k">${t(e)}</div><div class="v">${n}${r ? T`<span class="u">${r}</span>` : D}</div></div>`)}
    </div>`;
	}
	renderTab(e) {
		switch (this.tab) {
			case "overview": return this.renderOverview(e);
			case "controls": return this.renderControls(e);
			case "activity": return this.renderActivity(e);
			case "maintenance": return this.renderMaintenance(e);
			case "profile": return this.renderProfile(e);
			case "diagnostics": return this.renderDiagnostics(e);
		}
	}
	renderOverview(e) {
		let t = this.t, n = this.fmt, r = e.details, i = r.exercise ?? {}, a = e.device, o = e.alerts;
		return T`<div class="section">
      <div class="grid-2">
        <div class="card">
          <h2 class="card-title">${t("overview.status")}</h2>
          <div class="kv">
            ${this.kv(t("overview.state"), this.label(X.status, a.status))}
            ${this.kv(t("overview.mode_switch"), this.label(X.switchState, r.switchState))}
            ${this.kv(t("overview.power_source"), this.label(X.powerSource, r.powerSource))}
            ${this.kv(t("overview.last_run"), G(r.lastRanTimestamp, n))}
            ${this.kv(t("overview.active_alerts"), H(o.length || a.alertCount || 0, n))}
            ${a.shutdownReason && a.shutdownReason !== "None" ? this.kv(t("overview.shutdown_reason"), R(a.shutdownReason)) : D}
          </div>
        </div>
        <div class="card">
          <h2 class="card-title">${t("overview.next_exercise")}</h2>
          ${e.derived.has_schedule ? T`<div class="kv">
                ${this.kv(t("overview.when"), W(i.nextStartTimestamp, n))}
                ${this.kv(t("field.mode"), this.label(X.mode, i.mode))}
                ${this.kv(t("field.frequency"), this.label(X.frequency, i.frequency))}
                ${this.kv(t("field.duration"), wt(i.durationMinutes, n))}
                ${this.kv(t("overview.last_exercise"), G(i.lastStartTimestamp, n))}
              </div>` : T`<p class="empty">${t("overview.no_schedule")}</p>`}
        </div>
      </div>
      ${o.length ? T`<div class="card">
            <h2 class="card-title">${t("overview.active_alerts")}</h2>
            <div class="list">
              ${o.map((e) => T`<div class="list-item">
                  <div class=${`sev ${z(e.level)}`}></div>
                  <div class="when">${G(e.timestamp, n)}</div>
                  <div class="what">
                    <div class="title">${e.name || R(e.deviceEventId)}</div>
                    <div class="sub">${[this.label(X.level, e.level), e.isCriticalFault ? t("alert.critical") : ""].filter(Boolean).join(" · ")}</div>
                  </div>
                </div>`)}
            </div>
          </div>` : D}
    </div>`;
	}
	renderControls(e) {
		let t = this.t, n = e.derived, r = e.details.exercise ?? {}, i = e.available && !this.connectionError && n.is_connected, a = i && n.ready_to_run && !n.e_stop_engaged && n.supports_exercise_scheduling, o = n.supports_exercise_scheduling;
		return T`<div class="controls">
      <div class="card">
        <h2 class="card-title">${t("controls.remote_exercise")}</h2>
        <div class="btn-row">
          <button class="action" ?disabled=${!a || this.busy || n.is_exercising} @click=${this.askStart}>
            ${Z(nt)} ${t("controls.start")}
          </button>
          <button class="action danger ghost" ?disabled=${!i || this.busy || !n.is_exercising}
            @click=${() => this.call("stop_exercise", {}, "toast.exercise_stopped")}>
            ${Z(it)} ${t("controls.stop")}
          </button>
        </div>
        ${!n.ready_to_run && i ? T`<p class="hint">${t("controls.start_hint", { status: this.label(X.status, e.device.status) || t("common.unknown") })}</p>` : D}
      </div>

      ${o ? T`<div class="card">
            <h2 class="card-title">${n.has_schedule ? t("controls.schedule") : t("controls.create_schedule")}</h2>
            <div class="grid-2">
              <div class="field">
                <label for="freq">${t("field.frequency")}</label>
                <select id="freq" .value=${r.frequency || "EveryOtherWeek"}>
                  ${Vt.map((e) => T`<option value=${e} ?selected=${(r.frequency || "EveryOtherWeek") === e}>${this.label(X.frequency, e)}</option>`)}
                </select>
              </div>
              <div class="field">
                <label for="mode">${t("field.mode")}</label>
                <select id="mode" .value=${r.mode || "Unloaded"}>
                  ${Bt.map((e) => T`<option value=${e} ?selected=${(r.mode || "Unloaded") === e}>${this.label(X.mode, e)}</option>`)}
                </select>
              </div>
              <div class="field">
                <label for="dur">${t("controls.duration_minutes")}</label>
                <input id="dur" type="number" inputmode="numeric" min="5" max="60" step="1" required .value=${String(r.durationMinutes ?? 20)} />
              </div>
              ${n.supports_next_exercise_datetime ? T`<div class="field">
                    <label for="next">${t("controls.next_start")}</label>
                    <input id="next" type="datetime-local" .value=${At(r.nextStartTimestamp, this.fmt)} />
                  </div>` : D}
            </div>
            <div class="btn-row spaced">
              <button class="action" ?disabled=${!i || this.busy} @click=${this.saveSchedule}>${Z(Ge)} ${t("controls.save_schedule")}</button>
              ${n.has_schedule ? T`<button class="action ghost danger" ?disabled=${!i || this.busy} @click=${this.askDelete}>${Z(Ke)} ${t("controls.delete_schedule")}</button>` : D}
            </div>
          </div>` : T`<div class="card"><p class="muted">${t("controls.no_scheduling")}</p></div>`}

      <div class="card">
        <h2 class="card-title">${t("controls.controller")}</h2>
        <div class="btn-row">
          <button class="action ghost" ?disabled=${!i || this.busy}
            @click=${() => this.call("sync_controller_clock", {}, "toast.clock_synced")}>${Z(Je)} ${t("controls.sync_clock")}</button>
        </div>
        <p class="hint">${t("controls.controller_clock", { time: W(e.details.controllerClockTimestamp, this.fmt) })}</p>
      </div>

      <div class="card">
        <h2 class="card-title">${t("controls.add_note")}</h2>
        <div class="field"><textarea id="note" aria-label=${t("controls.note_label")} maxlength="2000" rows="2" placeholder=${t("controls.note_placeholder")}></textarea></div>
        <div class="btn-row spaced">
          <button class="action ghost" ?disabled=${this.busy} @click=${this.saveNote}>${Z($e)} ${t("controls.add_note_button")}</button>
        </div>
      </div>

      ${this.renderNotificationToggles(e)}
    </div>`;
	}
	renderNotificationToggles(e) {
		let t = this.account(e.entry_id), n = t?.notification_settings;
		return n ? T`<div class="card">
      <h2 class="card-title">${this.t("controls.notifications")}</h2>
      <div class="grid-2">
        ${Object.entries(n).filter(([, e]) => typeof e == "boolean").map(([n, r]) => T`<label class="toggle">
            <input type="checkbox" .checked=${He(r)} ?disabled=${this.busy || !t?.notification_entities?.[n]} @change=${(t) => this.toggleNotify(e, n, t.target.checked)} />
            <span>${this.notifyLabel(n)}</span>
          </label>`)}
      </div>
    </div>` : D;
	}
	renderActivity(e) {
		let t = this.t, n = this.fmt, r = e.events, i = e.notifications, a = (e, n, r) => n > e ? T`<div class="more"><button class="action ghost" @click=${r}>${t("common.show_more")}</button></div>` : D;
		return T`<div class="section">
      <div class="card">
        <h2 class="card-title">${t("activity.log")} <span class="pill">${H(r.length, n)}</span></h2>
        ${r.length ? T`<div class="list">${r.slice(0, this.eventLimit).map((e) => T`<div class="list-item">
                <div class=${`sev ${z(e.level)}`}></div>
                <div class="when">${W(e.timestamp, n)}</div>
                <div class="what">
                  <div class="title">${e.name || R(e.deviceEventId || e.event)}</div>
                  <div class="sub">${[
			this.label(X.level, e.level),
			e.type ? R(e.type) : "",
			e.fmi && e.fmi !== "swaggerGeneratedUnknown" ? t("activity.fmi", { value: R(e.fmi) }) : ""
		].filter(Boolean).join(" · ")}</div>
                </div>
              </div>`)}</div>${a(this.eventLimit, r.length, () => this.eventLimit += Y)}` : T`<p class="empty">${t("activity.none")}</p>`}
      </div>
      <div class="card">
        <h2 class="card-title">${t("activity.notifications")} <span class="pill">${H(i.length, n)}</span></h2>
        ${i.length ? T`<div class="list">${i.slice(0, this.notificationLimit).map((e) => T`<div class="list-item">
                <div class=${`sev ${z(e.type)}`}></div>
                <div class="when">${G(e.timestamp, n)}</div>
                <div class="what">
                  <div class="title">${e.message || this.label(X.notification, e.type)}</div>
                  <div class="sub">${[this.label(X.notification, e.type), e.isEStopEvent ? t("activity.estop") : ""].filter(Boolean).join(" · ")}</div>
                </div>
              </div>`)}</div>${a(this.notificationLimit, i.length, () => this.notificationLimit += Y)}` : T`<p class="empty">${t("activity.no_notifications")}</p>`}
      </div>
    </div>`;
	}
	renderMaintenance(e) {
		let t = this.t, n = this.fmt, r = e.device, i = e.maintenance_notes, a = H(e.details.runtimeSinceLastMaintenanceHours, n, 1);
		return T`<div class="section">
      <div class="card">
        <h2 class="card-title">${t("maintenance.title")}</h2>
        <div class="kv">
          ${this.kv(t("maintenance.last"), W(r.lastMaintenanceTimestamp, n))}
          ${this.kv(t("maintenance.next"), W(r.nextMaintenanceTimestamp, n))}
          ${this.kv(t("maintenance.interval"), r.maintenancePeriodDays ? Tt(r.maintenancePeriodDays, n) : "—")}
          ${this.kv(t("maintenance.runtime_since"), a === null ? "—" : `${a} h`)}
        </div>
      </div>
      <div class="card">
        <h2 class="card-title">${t("maintenance.history")} <span class="pill">${H(i.length, n)}</span></h2>
        ${i.length ? T`<div class="list">${i.map((e) => T`<div class="list-item">
                <div class="when">${W(e.timestamp, n)}</div>
                <div class="what">
                  <div class="title">${e.contents}</div>
                  <div class="sub">${e.authorIsDealer ? [t("maintenance.dealer"), e.dealerAuthor].filter(Boolean).join(" · ") : t("maintenance.homeowner")}</div>
                </div>
              </div>`)}</div>` : T`<p class="empty">${t("maintenance.none")}</p>`}
      </div>
    </div>`;
	}
	renderProfile(e) {
		let t = this.t, n = e.device, r = e.details, i = n.dealerOrgs?.[0] ?? {}, a = r.serviceAgreement ?? {}, o = H(r.setOutputVoltageV, this.fmt);
		return T`<div class="section">
      <div class="grid-2">
        <div class="card">
          <h2 class="card-title">${t("common.generator")}</h2>
          <div class="kv">
            ${this.kv(t("profile.model"), n.modelDisplayName || R(n.model))}
            ${this.kv(t("profile.serial"), n.serialNumber)}
            ${this.kv(t("profile.controller"), n.controllerType || R(n.product))}
            ${this.kv(t("profile.firmware"), n.firmwareVersion || n.currentFirmware)}
            ${this.kv(t("profile.fuel"), this.label(X.fuel, r.fuelType))}
            ${this.kv(t("profile.cooling"), this.label(X.cooling, r.coolingType))}
            ${this.kv(t("profile.rated_voltage"), o === null ? "—" : `${o} V`)}
          </div>
        </div>
        <div class="card">
          <h2 class="card-title">${t("profile.site")}</h2>
          <div class="kv">
            ${this.kv(t("profile.address"), gt(n.address) || "—")}
            ${this.kv(t("profile.connection"), this.label(X.connection, r.connectionType ?? n.connectionType))}
            ${this.kv(t("profile.service_agreement"), this.label(X.agreement, n.serviceAgreementStatus))}
            ${a.term ? this.kv(t("profile.term"), R(a.term)) : D}
            ${i.name ? this.kv(t("profile.dealer"), String(i.name)) : D}
            ${i.displayPhoneNumber ? this.kv(t("profile.dealer_phone"), String(i.displayPhoneNumber)) : D}
          </div>
        </div>
      </div>
      ${this.renderPeripherals(e)}
    </div>`;
	}
	renderPeripherals(e) {
		let t = this.t, n = e.available && !this.connectionError && e.derived.is_connected, r = [
			[
				t("profile.load_module"),
				e.details.loadShed,
				!1
			],
			[
				t("profile.pim"),
				e.details.pim,
				!1
			],
			[
				t("profile.transfer_switch"),
				e.details.ats,
				!0
			]
		].filter(([, e]) => e && Object.keys(e).length);
		return r.length ? T`<div class="grid-2">
      ${r.map(([e, r, i]) => {
			let a = r.parameters || [], o = n && r.isConnected !== !1;
			return T`<div class="card">
          <h2 class="card-title">${e}${"isConnected" in r ? T` <span class="pill">${r.isConnected ? t("profile.connected") : t("profile.offline")}</span>` : D}</h2>
          ${a.length ? T`<div class="params">${a.map((e) => this.renderParam(e, o))}</div>` : i ? T`<div class="kv">
                  ${this.kv(t("profile.model"), r.modelNo ?? "—")}
                  ${this.kv(t("profile.serial"), r.serialNumber ?? "—")}
                  ${this.kv(t("profile.position"), this.label(X.atsPosition, r.powerSource))}
                </div>` : T`<p class="hint">${t("profile.no_parameters")}</p>`}
        </div>`;
		})}
    </div>` : D;
	}
	renderParam(e, t) {
		let n = String(e.displayName ?? `#${e.definitionId}`), r = t && !e.isReadOnly && e.definitionId !== void 0, i = e.value;
		return T`<div class="param">
      <span class="key">${n}</span>
      ${r && typeof i == "boolean" ? T`<input type="checkbox" aria-label=${n} .checked=${He(i)} ?disabled=${this.busy}
            @change=${(t) => this.setParam(e, t.target.checked)} />` : T`<span class="val">${this.paramValue(i)}</span>`}
      ${r ? T`<button class="icon-button small" title=${this.t("profile.edit", { name: n })} aria-label=${this.t("profile.edit", { name: n })}
            ?disabled=${this.busy} @click=${() => this.openEdit(e, n)}>${Z(tt)}</button>` : D}
    </div>`;
	}
	renderEdit() {
		let e = this.editing;
		if (!e) return D;
		let t = this.t, n = typeof e.value == "number";
		return T`<div class="scrim" @click=${this.closeEdit} @keydown=${this.onEditKey}>
      <form class="dialog" role="dialog" aria-modal="true" aria-labelledby="edit-title" novalidate
        @click=${(e) => e.stopPropagation()} @submit=${this.saveEdit}>
        <h2 id="edit-title">${t("edit.title")}</h2>
        <div class="field">
          <label for="edit-name">${t("edit.name")}</label>
          <input id="edit-name" type="text" maxlength="64" autocomplete="off" .value=${e.name} />
        </div>
        ${n || typeof e.value == "string" ? T`<div class="field">
              <label for="edit-value">${t("edit.value")}</label>
              <input id="edit-value" type=${n ? "number" : "text"} step="any" maxlength="255" autocomplete="off"
                .value=${String(e.value)} />
            </div>` : D}
        <div class="btn-row end">
          <button type="button" class="action ghost" @click=${this.closeEdit}>${t("common.cancel")}</button>
          <button type="submit" class="action">${t("edit.save")}</button>
        </div>
      </form>
    </div>`;
	}
	renderDiagnostics(e) {
		let t = this.t, n = this.fmt, r = this.account(e.entry_id), i = (e) => {
			let t = H(e, n);
			return t === null ? null : `${t}%`;
		}, a = e.details.autoFirmwareUpdateEnabled, o = [
			[t("diagnostics.connected"), e.derived.is_connected ? t("common.yes") : t("common.no")],
			[t("diagnostics.device_ip"), e.derived.ip_address],
			[t("diagnostics.mac"), e.derived.mac_address],
			[t("diagnostics.uptime"), i(e.device.uptimePercent)],
			[t("diagnostics.last_connected"), W(e.device.lastConnectedTimestamp, n)],
			[t("diagnostics.parameters_updated"), G(e.device.latestParameterUpdateTimestamp, n)],
			[t("diagnostics.cellular_status"), this.label(X.cellular, e.details.cellularDataStatus)],
			[t("diagnostics.cellular_used"), i(e.details.cellularDataPercentage)],
			[t("diagnostics.auto_update"), typeof a == "boolean" ? this.paramValue(a) : null],
			[t("diagnostics.details_refreshed"), G(e.details_updated, n)],
			[t("diagnostics.feeds_refreshed"), G(e.feeds_updated, n)],
			[t("diagnostics.account"), r?.last_update_success === !1 ? t("diagnostics.account_failed") : t("diagnostics.account_ok")]
		];
		return T`<div class="section">
      <div class="card">
        <h2 class="card-title">${t("diagnostics.title")}</h2>
        <div class="kv">${o.filter(([, e]) => e != null && e !== "").map(([e, t]) => this.kv(e, t))}</div>
      </div>
      <div class="card">
        <h2 class="card-title">${t("diagnostics.entities")}</h2>
        <p class="hint">${t("diagnostics.entities_text", { count: H(Object.keys(e.entities).length, n) ?? "0" })}</p>
        ${e.ha_device_id ? T`<div class="btn-row spaced">${this.link(`/config/devices/device/${e.ha_device_id}`, t("diagnostics.open_device"), "action ghost")}</div>` : D}
      </div>
    </div>`;
	}
	renderConfirm() {
		let e = this.confirm;
		return e ? T`<div class="scrim" @click=${this.closeConfirm} @keydown=${this.onConfirmKey}>
      <div class="dialog" role="alertdialog" aria-modal="true" aria-labelledby="confirm-title" aria-describedby="confirm-text"
        @click=${(e) => e.stopPropagation()}>
        <h2 id="confirm-title">${e.title}</h2>
        <p id="confirm-text">${e.text}</p>
        <div class="btn-row end">
          <button id="confirm-cancel" class="action ghost" @click=${this.closeConfirm}>${this.t("common.cancel")}</button>
          <button id="confirm-ok" class=${`action ${e.danger ? "danger" : ""}`}
            @click=${() => {
			this.confirm = null, e.run();
		}}>${e.action}</button>
        </div>
      </div>
    </div>` : D;
	}
	kv(e, t) {
		return T`<div class="key">${e}</div><div class="val">${t == null || t === "" ? "—" : String(t)}</div>`;
	}
	link(e, t, n) {
		return T`<a class=${n} href=${e} @click=${(t) => this.navigate(t, e)}>${Z(et)} ${t}</a>`;
	}
	paramValue(e) {
		return typeof e == "boolean" ? e ? this.t("common.on") : this.t("common.off") : e == null ? "—" : typeof e == "number" ? H(e, this.fmt, +!Number.isInteger(e)) ?? "—" : String(e);
	}
	statusText(e, t) {
		return t === "running" ? this.t(e.derived.utility_present === !1 ? "status.running_outage" : "status.running") : t === "standby" ? e.derived.ready_to_run ? this.t("status.ready") : this.label(X.status, e.device.status) || this.t("status.standby") : this.t(Ut[t]);
	}
	chipColor(e) {
		return e === "offline" ? "var(--rk-muted)" : e === "fault" || e === "estop" ? "var(--rk-bad)" : e === "exercising" ? "var(--rk-util)" : "var(--rk-ok)";
	}
	toggleMenu() {
		this.dispatchEvent(new CustomEvent("hass-toggle-menu", {
			bubbles: !0,
			composed: !0
		}));
	}
	refresh() {
		this.connectionError ? this.subscribe() : this.call("refresh", {}, "toast.refreshed");
	}
	navigate(e, t) {
		e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || (e.preventDefault(), history.pushState(null, "", t), window.dispatchEvent(new CustomEvent("location-changed", { detail: { replace: !1 } })));
	}
	onPick(e) {
		this.selected = e.target.value, this.tab = "overview", this.eventLimit = Y, this.notificationLimit = Y;
	}
	onTabKey(e) {
		let t = J.indexOf(this.tab), n = e.key === "ArrowRight" ? t + 1 : e.key === "ArrowLeft" ? t - 1 : e.key === "Home" ? 0 : e.key === "End" ? J.length - 1 : null;
		n !== null && (e.preventDefault(), this.tab = J[(n + J.length) % J.length], this.updateComplete.then(() => this.field(`tab-${this.tab}`)?.focus()));
	}
	ask(e) {
		this.rememberFocus(), this.confirm = e;
	}
	askStart() {
		this.ask({
			title: this.t("confirm.start.title"),
			text: this.t("confirm.start.text"),
			action: this.t("confirm.start.action"),
			danger: !1,
			run: () => void this.call("start_exercise", {}, "toast.exercise_started")
		});
	}
	askDelete() {
		this.ask({
			title: this.t("confirm.delete.title"),
			text: this.t("confirm.delete.text"),
			action: this.t("confirm.delete.action"),
			danger: !0,
			run: () => void this.call("delete_exercise_schedule", {}, "toast.schedule_deleted")
		});
	}
	closeConfirm() {
		this.confirm = null;
	}
	onConfirmKey(e) {
		e.key === "Escape" ? this.closeConfirm() : this.keepFocusInDialog(e);
	}
	keepFocusInDialog(e) {
		if (e.key !== "Tab") return;
		let t = [...this.renderRoot.querySelectorAll(".dialog input, .dialog button")];
		t.length && (e.preventDefault(), t[(t.indexOf(this.renderRoot.activeElement) + (e.shiftKey ? -1 : 1) + t.length) % t.length].focus());
	}
	rememberFocus() {
		this.restoreFocus = this.renderRoot instanceof ShadowRoot ? this.renderRoot.activeElement : null;
	}
	openEdit(e, t) {
		this.rememberFocus(), this.editing = {
			definitionId: e.definitionId,
			name: t,
			value: e.value
		};
	}
	closeEdit() {
		this.editing = null;
	}
	onEditKey(e) {
		e.key === "Escape" ? this.closeEdit() : this.keepFocusInDialog(e);
	}
	async setParam(e, t) {
		await this.call("set_peripheral_value", {
			definition_id: String(e.definitionId),
			value: t
		}, "toast.setting_saved"), this.requestUpdate();
	}
	async saveEdit(e) {
		e.preventDefault();
		let t = this.editing;
		if (!t) return;
		let n = this.field("edit-name")?.value.trim() ?? "";
		if (!n) {
			this.showToast(this.t("toast.name_required"), !0);
			return;
		}
		let r = this.field("edit-value"), i = t.value;
		if (r && (i = typeof t.value == "number" ? Number(r.value) : r.value, r.value.trim() === "" || typeof i == "number" && !Number.isFinite(i))) {
			this.showToast(this.t("toast.value_invalid"), !0);
			return;
		}
		this.editing = null;
		let a = String(t.definitionId);
		(n === t.name || await this.call("rename_peripheral", {
			definition_id: a,
			name: n
		}, "toast.setting_saved")) && i !== t.value && await this.call("set_peripheral_value", {
			definition_id: a,
			value: i
		}, "toast.setting_saved");
	}
	field(e) {
		return this.renderRoot.querySelector(`#${e}`);
	}
	async saveSchedule() {
		for (let e of this.renderRoot.querySelectorAll(".field input")) if (!e.reportValidity()) return;
		let e = this.field("freq")?.value, t = this.field("mode")?.value, n = this.field("dur")?.value, r = this.field("next")?.value, i = {};
		if (e && (i.frequency = e), t && (i.mode = t), n && (i.duration = Number(n)), r) {
			let e = jt(r, this.fmt);
			if (!e) {
				this.showToast(this.t("toast.invalid_next_start"), !0);
				return;
			}
			i.next_start = e.toISOString();
		}
		await this.call("set_exercise_schedule", i, "toast.schedule_saved");
	}
	async saveNote() {
		let e = this.field("note"), t = e?.value.trim();
		t ? await this.call("add_maintenance_note", { note: t }, "toast.note_added") && e && (e.value = "") : this.showToast(this.t("toast.note_required"), !0);
	}
	async toggleNotify(e, t, n) {
		if (this.busy) return;
		let r = this.account(e.entry_id)?.notification_entities?.[t];
		if (!r) this.showToast(this.t("toast.notify_unavailable"), !0);
		else {
			this.busy = !0;
			try {
				await this.hass.callService("switch", n ? "turn_on" : "turn_off", { entity_id: r });
			} catch (e) {
				this.showToast(Wt(e, this.t("toast.setting_failed")), !0);
			} finally {
				this.busy = !1, this.requestUpdate();
			}
		}
	}
};
q([F({ attribute: !1 })], $.prototype, "hass", void 0), q([F({ attribute: !1 })], $.prototype, "panel", void 0), q([F({
	type: Boolean,
	reflect: !0
})], $.prototype, "narrow", void 0), q([I()], $.prototype, "snapshot", void 0), q([I()], $.prototype, "selected", void 0), q([I()], $.prototype, "tab", void 0), q([I()], $.prototype, "busy", void 0), q([I()], $.prototype, "toast", void 0), q([I()], $.prototype, "connectionError", void 0), q([I()], $.prototype, "receivedSnapshot", void 0), q([I()], $.prototype, "confirm", void 0), q([I()], $.prototype, "editing", void 0), q([I()], $.prototype, "eventLimit", void 0), q([I()], $.prototype, "notificationLimit", void 0), $ = q([Me("rehlko-energy-panel")], $);
export { $ as RehlkoEnergyPanel };
