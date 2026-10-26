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

/* Decorative pixel sprites. Each one is drawn on a small grid with crisp edges,
   reads its colours from the theme tokens and is hidden from screen readers. */

type Px = [number, number, number, number, string];

function Sprite({
  cells,
  viewBox,
  className,
}: {
  cells: Px[];
  viewBox: string;
  className?: string;
}): ReactNode {
  return (
    <svg
      className={className}
      viewBox={viewBox}
      shapeRendering="crispEdges"
      aria-hidden="true"
      focusable="false">
      {cells.map(([x, y, w, h, c], i) => (
        <rect key={i} x={x} y={y} width={w} height={h} className={`px-c-${c}`} />
      ))}
    </svg>
  );
}

const disc: Array<[number, number, number, number]> = [
  [5, 0, 6, 1],
  [3, 1, 10, 1],
  [2, 2, 12, 1],
  [1, 3, 14, 2],
  [0, 5, 16, 6],
  [1, 11, 14, 2],
  [2, 13, 12, 1],
  [3, 14, 10, 1],
  [5, 15, 6, 1],
];

const sun: Px[] = [
  ...disc.map(([x, y, w, h]): Px => [x, y, w, h, 'sun']),
  [3, 11, 10, 2, 'sun-shade'],
  [5, 13, 6, 2, 'sun-shade'],
  [4, 3, 3, 2, 'cloud'],
];

const moon: Px[] = [
  ...disc.map(([x, y, w, h]): Px => [x, y, w, h, 'moon']),
  [4, 4, 3, 3, 'moon-shade'],
  [10, 7, 2, 2, 'moon-shade'],
  [6, 11, 3, 2, 'moon-shade'],
];

const cloud: Px[] = [
  [7, 0, 6, 1, 'cloud'],
  [5, 1, 10, 2, 'cloud'],
  [15, 2, 5, 2, 'cloud'],
  [2, 3, 20, 3, 'cloud'],
  [0, 6, 24, 3, 'cloud'],
  [2, 9, 20, 1, 'cloud-shade'],
  [0, 8, 2, 1, 'cloud-shade'],
  [22, 8, 2, 1, 'cloud-shade'],
];

const fencePosts = [52, 64, 76, 88, 100, 112, 124];
const sprouts = [58, 70, 82, 94, 106, 118];

const farm: Px[] = [
  // Apple tree
  [24, 30, 4, 18, 'trunk'],
  [22, 46, 8, 2, 'trunk'],
  [20, 6, 12, 4, 'leaf'],
  [16, 10, 20, 6, 'leaf'],
  [13, 16, 26, 8, 'leaf'],
  [15, 24, 22, 4, 'leaf-dark'],
  [19, 28, 14, 2, 'leaf-dark'],
  [20, 10, 6, 3, 'leaf-light'],
  [16, 16, 4, 3, 'leaf-light'],
  [18, 19, 2, 2, 'fruit'],
  [29, 14, 2, 2, 'fruit'],
  [33, 21, 2, 2, 'fruit'],
  [24, 24, 2, 2, 'fruit'],
  // Fence
  [50, 37, 78, 2, 'wood-light'],
  [50, 43, 78, 2, 'wood-light'],
  ...fencePosts.map((x): Px => [x, 34, 3, 14, 'wood']),
  ...fencePosts.map((x): Px => [x, 33, 3, 1, 'wood-dark']),
  // Sprouts by the fence
  ...sprouts.flatMap((x): Px[] => [
    [x, 44, 1, 4, 'leaf'],
    [x - 1, 44, 1, 1, 'leaf-light'],
    [x + 1, 43, 1, 1, 'leaf-light'],
  ]),
  // Farmhouse
  [172, 10, 4, 10, 'wall-shade'],
  [171, 9, 6, 1, 'wood-dark'],
  [140, 24, 44, 4, 'roof-dark'],
  [144, 20, 36, 4, 'roof'],
  [148, 16, 28, 4, 'roof'],
  [152, 12, 20, 4, 'roof'],
  [156, 8, 12, 4, 'roof'],
  [144, 28, 36, 20, 'wall'],
  [144, 28, 36, 2, 'wall-shade'],
  [178, 28, 2, 20, 'wall-shade'],
  [158, 34, 8, 14, 'wood'],
  [158, 34, 8, 1, 'wood-dark'],
  [164, 41, 1, 1, 'wood-light'],
  [148, 32, 6, 6, 'window'],
  [170, 32, 6, 6, 'window'],
  [151, 32, 1, 6, 'wood-dark'],
  [148, 35, 6, 1, 'wood-dark'],
  [173, 32, 1, 6, 'wood-dark'],
  [170, 35, 6, 1, 'wood-dark'],
  // Sunflower
  [192, 34, 1, 14, 'leaf'],
  [193, 40, 2, 1, 'leaf'],
  [190, 29, 5, 5, 'flower'],
  [191, 30, 3, 3, 'flower-heart'],
];

const featureIcons: Px[][] = [
  // A sprout in a seed bed: planning before planting
  [
    [7, 3, 2, 9, 'leaf'],
    [3, 3, 4, 2, 'leaf-light'],
    [2, 2, 2, 2, 'leaf-light'],
    [9, 5, 4, 2, 'leaf'],
    [12, 4, 2, 2, 'leaf'],
    [1, 12, 14, 3, 'trunk'],
    [1, 12, 14, 1, 'wood-light'],
  ],
  // A tick on a crate: checked work
  [
    [1, 2, 14, 13, 'wood'],
    [2, 3, 12, 11, 'wood-light'],
    [2, 8, 12, 1, 'wood'],
    [3, 8, 2, 2, 'check'],
    [5, 10, 2, 2, 'check'],
    [7, 8, 2, 2, 'check'],
    [9, 6, 2, 2, 'check'],
    [11, 4, 2, 2, 'check'],
  ],
  // A scroll: the plain report
  [
    [3, 1, 10, 14, 'paper'],
    [2, 1, 12, 2, 'wood-light'],
    [2, 13, 12, 2, 'wood-light'],
    [5, 5, 6, 1, 'ink'],
    [5, 7, 6, 1, 'ink'],
    [5, 9, 4, 1, 'ink'],
  ],
];

export default function Home(): ReactNode {
  return (
    <Layout
      title="Home"
      description="Agentville gives Claude a small team of helpers that plan, do, check and report your work.">
      <header className="hero hero--primary hero-agentville">
        <div className="px-sky" aria-hidden="true">
          <span className="px-stars" />
          <Sprite className="px-sun" viewBox="0 0 16 16" cells={sun} />
          <Sprite className="px-moon" viewBox="0 0 16 16" cells={moon} />
          <Sprite className="px-cloud px-cloud--1" viewBox="0 0 24 10" cells={cloud} />
          <Sprite className="px-cloud px-cloud--2" viewBox="0 0 24 10" cells={cloud} />
          <Sprite className="px-cloud px-cloud--3" viewBox="0 0 24 10" cells={cloud} />
        </div>
        <div className="container">
          <div className="px-sign">
            <Heading as="h1" className="hero__title">
              Agentville
            </Heading>
            <p className="hero__subtitle">
              A small team of helpers for Claude that plans, does, checks and reports your work.
            </p>
          </div>
          <div className="hero-agentville__buttons">
            <Link className="button button--secondary button--lg" to="/docs/get-started">
              Get started in Claude Chat
            </Link>
            <Link className="button button--outline button--secondary button--lg" to="/docs/intro">
              What is Agentville?
            </Link>
          </div>
        </div>
        <div className="px-farm" aria-hidden="true">
          <svg viewBox="0 0 200 48" preserveAspectRatio="xMidYMax meet" shapeRendering="crispEdges" focusable="false">
            {farm.map(([x, y, w, h, c], i) => (
              <rect key={i} x={x} y={y} width={w} height={h} className={`px-c-${c}`} />
            ))}
          </svg>
          <div className="px-ground" />
        </div>
      </header>
      <main>
        <section className="features-agentville">
          <div className="container">
            <div className="row">
              {features.map((feature, index) => (
                <div key={feature.title} className="col col--4">
                  <div className="px-slot">
                    <Sprite className="px-icon" viewBox="0 0 16 16" cells={featureIcons[index]} />
                    <Heading as="h2">{feature.title}</Heading>
                    <p>{feature.body}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>
    </Layout>
  );
}
