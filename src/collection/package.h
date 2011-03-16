// This file is part of File Collection Manager
// Copyright (C) 2009 Brian Allen Vanderburg II
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 3 of the License, or
// (at your option) any later version.


// Header guard
#ifndef __FCMAN_COLLECTION_PACKAGE_H
#define __FCMAN_COLLECTION_PACKAGE_H


// Requirements
#include <list>

#include <wx/defs.h>
#include <wx/string.h>

#include "version.h"


class WXDLLIMPEXP_XML wxXmlNode;

class File;
class Dependency;


// Package object
class Package;
typedef std::list<Package*> PackageList;

class Package
{
public:
    // ctor/dtor
    Package();
    Package(wxXmlNode* node);

    ~Package();

    // Information
    void SetName(const wxString& name);
    const wxString& GetName() const { return m_name; }

    void SetVersion(const wxString& version);
    const wxString& GetVersion() const { return m_version.Get(); }
    const Version& GetVersionObject() const { return m_version; }

    wxString GetDisplayString() const;

    // Actions
    wxXmlNode* Save();

    void Delete();

protected:
    // Information
    File* m_file;
    wxString m_name;
    Version m_version;

private:
    // No copy or assign
    Package(const Package& copy);
    Package& operator=(const Package& rhs);
    

friend class File;
};


#endif // Header guard



