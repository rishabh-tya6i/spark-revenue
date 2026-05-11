import React from 'react';

interface PageContainerProps {
  children: React.ReactNode;
  title?: string;
}

const PageContainer: React.FC<PageContainerProps> = ({ children, title }) => {
  return (
    <div className="page-content grid-bg">
      {title && (
        <h1 style={{ marginBottom: '32px', fontSize: '2.5rem' }}>{title}</h1>
      )}
      {children}
    </div>
  );
};

export default PageContainer;
