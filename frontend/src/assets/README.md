# Generator product imagery

These are manufacturer product images from the KOHLER Home Energy / Rehlko website,
retrieved 2026-11-12. They retain the original enclosure, branding, proportions and
transparency. They were requested from the manufacturer's image CDN at 1000 px width,
in WebP with alpha (`wid=1000&fmt=webp-alpha&qlt=88`). No generative imaging was used.

Product imagery and trademarks remain the property of their respective owners. These
third-party images are not covered by the repository's Apache-2.0 source-code license.
They identify the equipment supported by this unofficial integration.

| Local image | Manufacturer product page | Original CDN image |
| --- | --- | --- |
| `generator-rca.webp` | [26RCA](https://www.kohlerhomeenergy.rehlko.com/products/home-generators/26rca), [20RCA](https://www.kohlerhomeenergy.rehlko.com/products/home-generators/20rca), [14RCA](https://www.kohlerhomeenergy.rehlko.com/products/home-generators/14rca) — these pages use the same enclosure image | [aac11780_rgb](https://s7d9.scene7.com/is/image/discoveryenergy/aac11780_rgb) |
| `generator-resv.webp` | [12RESV](https://www.kohlerhomeenergy.rehlko.com/products/home-generators/12resv) | [zab61930_rgb](https://s7d9.scene7.com/is/image/discoveryenergy/zab61930_rgb) |
| `generator-rcla.webp` | [30RCLA](https://www.kohlerhomeenergy.rehlko.com/products/home-generators/30rcla) | [zab60904_rgb](https://s7d9.scene7.com/is/image/discoveryenergy/zab60904_rgb) |
| `generator-rclc.webp` | [48RCLC](https://www.kohlerhomeenergy.rehlko.com/products/home-generators/48rclc) | [aab57806_rgb](https://s7d9.scene7.com/is/image/discoveryenergy/aab57806_rgb) |

`generator-visual.ts` selects verified model matches and labels images of other models
as representative. Actual model names remain visible in the Profile tab. Add new verified
images and model rules here as coverage expands; do not claim a family image is an exact
photo of an unsupported model. Images are embedded by Vite library mode in the shipped
JavaScript, so installed panels make no image requests to third-party websites.
