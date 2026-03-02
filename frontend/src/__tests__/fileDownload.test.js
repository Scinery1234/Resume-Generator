/**
 * Tests for fileDownload utility
 */
import { downloadBlob } from '../utils/fileDownload';

// Mock URL.createObjectURL and URL.revokeObjectURL
global.URL.createObjectURL = jest.fn(() => 'mock-url');
global.URL.revokeObjectURL = jest.fn();

// Mock document.createElement and related methods
const mockClick = jest.fn();
const mockAppendChild = jest.fn();
const mockRemoveChild = jest.fn();

beforeEach(() => {
  document.createElement = jest.fn(() => ({
    href: '',
    download: '',
    click: mockClick,
  }));
  document.body.appendChild = mockAppendChild;
  document.body.removeChild = mockRemoveChild;
  jest.clearAllMocks();
});

describe('downloadBlob', () => {
  test('creates download link and triggers download', () => {
    const blob = new Blob(['test content'], { type: 'application/pdf' });
    const filename = 'test.pdf';
    
    downloadBlob(blob, filename);
    
    expect(document.createElement).toHaveBeenCalledWith('a');
    expect(mockAppendChild).toHaveBeenCalled();
    expect(mockClick).toHaveBeenCalled();
    expect(mockRemoveChild).toHaveBeenCalled();
    expect(global.URL.createObjectURL).toHaveBeenCalledWith(blob);
    expect(global.URL.revokeObjectURL).toHaveBeenCalledWith('mock-url');
  });

  test('throws error on failure', () => {
    document.createElement = jest.fn(() => {
      throw new Error('Create element failed');
    });
    
    const blob = new Blob(['test'], { type: 'text/plain' });
    
    expect(() => downloadBlob(blob, 'test.txt')).toThrow('Failed to download file');
  });
});
