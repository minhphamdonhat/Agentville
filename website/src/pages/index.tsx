import type {ReactNode} from 'react';
import Link from '@docusaurus/Link';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';

type Feature = {
  title: string;
  body: string;
};

const features: Feature[] = [
  {
    title: 'It plans before it works',
    body: 'For anything bigger than a quick fix, Agentville talks the request through with you and writes a short plan before it changes anything.',
  },
  {
    title: 'Its work is checked',
    body: 'A separate helper checks the result, and another reviews it, so you get evidence rather than a promise.',
  },
  {
    title: 'It tells you what is left',
    body: 'Every request ends with a plain report: what was done, what was checked and any decision that is still yours.',
  },
];

export default function Home(): ReactNode {
  return (
    <Layout
      title="Home"
      description="Agentville gives Claude a small team of helpers that plan, do, check and report your work.">
      <header className="hero hero--primary hero-agentville">
        <div className="container">
          <Heading as="h1" className="hero__title">
            Agentville
          </Heading>
          <p className="hero__subtitle">
            A small team of helpers for Claude that plans, does, checks and reports your work.
          </p>
          <div className="hero-agentville__buttons">
            <Link className="button button--secondary button--lg" to="/docs/get-started">
              Get started in Claude Chat
            </Link>
            <Link className="button button--outline button--secondary button--lg" to="/docs/intro">
              What is Agentville?
            </Link>
          </div>
        </div>
      </header>
      <main>
        <section className="features-agentville">
          <div className="container">
            <div className="row">
              {features.map((feature) => (
                <div key={feature.title} className="col col--4">
                  <Heading as="h2">{feature.title}</Heading>
                  <p>{feature.body}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>
    </Layout>
  );
}
