import type {ReactNode} from 'react';
import Link from '@docusaurus/Link';
import useBaseUrl from '@docusaurus/useBaseUrl';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';

type Feature = {
  title: string;
  body: string;
  accent: 'leaf' | 'sun' | 'roof';
};

const features: Feature[] = [
  {
    title: 'It plans before it works',
    body: 'For anything bigger than a quick fix, Agentville talks the request through with you and writes a short plan before it changes anything.',
    accent: 'leaf',
  },
  {
    title: 'Its work is checked',
    body: 'A separate helper checks the result, and another reviews it, so you get evidence rather than a promise.',
    accent: 'sun',
  },
  {
    title: 'It tells you what is left',
    body: 'Every request ends with a plain report: what was done, what was checked and any decision that is still yours.',
    accent: 'roof',
  },
];

export default function Home(): ReactNode {
  const wordmark = useBaseUrl('/img/wordmark.png');
  const house = useBaseUrl('/img/house-isometric.png');
  return (
    <Layout
      title="Home"
      description="Agentville gives Claude a small team of helpers that plan, do, check and report your work.">
      <header className="av-hero">
        <div className="container av-hero__inner">
          <div className="av-hero__text">
            <Heading as="h1" className="av-hero__title">
              <img
                className="av-pixel-art av-hero__wordmark"
                src={wordmark}
                alt="Agentville"
                width={520}
                height={212}
              />
            </Heading>
            <p className="av-hero__subtitle">
              A small team of helpers for Claude that plans, does, checks and reports your work.
            </p>
            <div className="av-hero__buttons">
              <Link className="button button--primary button--lg" to="/docs/get-started">
                Get started in Claude Chat
              </Link>
              <Link className="button button--secondary button--lg" to="/docs/intro">
                What is Agentville?
              </Link>
            </div>
          </div>
          <div className="av-hero__art">
            <img
              className="av-pixel-art av-hero__house"
              src={house}
              alt=""
              aria-hidden="true"
              width={420}
              height={407}
            />
          </div>
        </div>
      </header>
      <main>
        <section className="av-features">
          <div className="container">
            <div className="av-features__grid">
              {features.map((feature) => (
                <article key={feature.title} className="av-card">
                  <span className={`av-card__bar av-card__bar--${feature.accent}`} aria-hidden="true" />
                  <Heading as="h2">{feature.title}</Heading>
                  <p>{feature.body}</p>
                </article>
              ))}
            </div>
          </div>
        </section>
      </main>
    </Layout>
  );
}
